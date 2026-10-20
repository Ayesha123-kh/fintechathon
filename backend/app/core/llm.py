"""Direct calls to the self-hosted models (vLLM, OpenAI-compatible).

Agents run inside OpenMausBot; the backend only uses the LLM for small structured jobs
(email transaction extraction, merchant categorisation) and speech-to-text.
"""

import base64
import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from app.core.config import settings

log = logging.getLogger(__name__)

llm = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key or "EMPTY", timeout=60)
stt = AsyncOpenAI(base_url=settings.stt_base_url, api_key=settings.stt_api_key or "EMPTY", timeout=120)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


# How to ask for plain JSON without thinking differs by server. vLLM: json_object + chat_template_kwargs.
# LM Studio rejects json_object and ignores chat_template_kwargs (the model then spends max_tokens thinking and
# returns nothing), but honours reasoning_effort="none". Try vLLM style first; remember whichever the server accepts.
_STYLES = [
    {"response_format": {"type": "json_object"}, "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
    {"reasoning_effort": "none", "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
]
_style = 0


async def complete_json(system: str, user: str, max_tokens: int = 800) -> dict[str, Any] | None:
    """Ask for a JSON object. Thinking is disabled for these short extraction calls."""
    global _style
    for i in range(_style, len(_STYLES)):
        try:
            resp = await llm.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0,
                max_tokens=max_tokens,
                **_STYLES[i],
            )
            _style = i
            break
        except BadRequestError as exc:  # this server doesn't take these options: try the next style
            log.info("LLM rejected request style %d: %s", i, exc)
        except Exception as exc:  # model offline, timeout ...
            log.warning("LLM call failed: %s", exc)
            return None
    else:
        log.warning("LLM call failed: no request style accepted")
        return None
    content = resp.choices[0].message.content or ""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    match = _JSON_BLOCK.search(content)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


# Qwen3-ASR has no Urdu: Urdu speech comes back tagged "Hindi" and written in Devanagari, whichever
# language the prompt asks for. It answers "language X<asr_text>the words", so a grammar (llama.cpp)
# keeps English in Latin letters and makes Hindi/Urdu come out in Roman Urdu (or Urdu script).
_LATIN = r"[\x20-\x7E\n]*"
_URDU = r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF0-9 \n]*"  # Arabic-script letters, Urdu punctuation


# OpenAI's own speech-to-text (whisper-1, gpt-4o-mini-transcribe ...) is an audio endpoint, not a chat model, and it
# knows nothing about grammars. Used when STT_BASE_URL is api.openai.com; the prompt steers Urdu into Roman Urdu.
_OPENAI_PROMPT_LATIN = (
    "The speaker may use English, Urdu or Hindi. Write English in English. Write Urdu or Hindi speech in Roman Urdu "
    "(Urdu in Latin letters), for example: mujhe sasta khana chahiye."
)
_OPENAI_PROMPT_URDU = "اردو میں لکھیں۔ English words may stay in English."


def _openai_stt() -> bool:
    return "api.openai.com" in str(settings.stt_base_url)


async def _transcribe_openai(wav: bytes, urdu_script: bool) -> str:
    resp = await stt.audio.transcriptions.create(
        model=settings.stt_model,
        file=("voice.wav", wav, "audio/wav"),
        prompt=_OPENAI_PROMPT_URDU if urdu_script else _OPENAI_PROMPT_LATIN,
        temperature=0,
    )
    return (resp.text or "").strip()


async def transcribe(wav: bytes, urdu_script: bool = False) -> str:
    if _openai_stt():
        return await _transcribe_openai(wav, urdu_script)
    seconds = (len(wav) - 44) / max(1, int.from_bytes(wav[28:32], "little"))  # WAV header byte rate
    urdu = _URDU if urdu_script else _LATIN
    resp = await stt.chat.completions.create(
        model=settings.stt_model,
        messages=[{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": base64.b64encode(wav).decode(), "format": "wav"}},
        ]}],
        temperature=0,
        max_tokens=64 + int(seconds * 15),  # a constrained decode can start repeating itself
        extra_body={"grammar": f'root ::= "language " ("English<asr_text>" {_LATIN} | ("Hindi" | "Urdu") "<asr_text>" {urdu})'},
    )
    return (resp.choices[0].message.content or "").split("<asr_text>")[-1].strip()
