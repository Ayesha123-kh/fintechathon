"""Direct calls to the self-hosted models (vLLM, OpenAI-compatible).

Agents run inside OpenMausBot; the backend only uses the LLM for small structured jobs
(email transaction extraction, merchant categorisation) and speech-to-text.
"""

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

log = logging.getLogger(__name__)

llm = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key or "EMPTY", timeout=60)
stt = AsyncOpenAI(base_url=settings.stt_base_url, api_key=settings.stt_api_key or "EMPTY", timeout=120)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


async def complete_json(system: str, user: str, max_tokens: int = 800) -> dict[str, Any] | None:
    """Ask for a JSON object. Thinking is disabled for these short extraction calls."""
    try:
        resp = await llm.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    except Exception as exc:  # model offline, timeout ...
        log.warning("LLM call failed: %s", exc)
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
