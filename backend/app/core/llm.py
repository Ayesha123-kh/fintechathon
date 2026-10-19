"""Direct calls to the self-hosted models (vLLM, OpenAI-compatible).

Agents run inside OpenMausBot; the backend only uses the LLM for small structured jobs
(email transaction extraction, merchant categorisation) and speech-to-text.
"""

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


async def transcribe(filename: str, data: bytes, content_type: str) -> str:
    resp = await stt.audio.transcriptions.create(
        model=settings.stt_model, file=(filename, data, content_type)
    )
    return (resp.text or "").strip()
