import logging
import os
import time
from typing import Optional

import httpx
from fastapi import HTTPException

DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
# A single slow/stalled call must not be able to block a synchronous HTTP
# request for minutes - a multi-leg trip makes several of these sequentially,
# so a generous per-call timeout compounds badly (e.g. 180s x 5 legs = 15min).
DEEPSEEK_TIMEOUT_SECONDS = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30"))

logger = logging.getLogger("planner.llm")


def normalize_llm_provider(value: Optional[str] = None) -> str:
    """Always DeepSeek."""
    return "deepseek"


async def _call_deepseek(prompt: str) -> str:
    key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="DeepSeek is not configured. Set DEEPSEEK_API_KEY in the server environment.",
        )
    url = f"{DEEPSEEK_API_BASE}/chat/completions"
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            elapsed = time.monotonic() - started
            if response.status_code >= 400:
                text = response.text[:500]
                logger.warning("DeepSeek call failed after %.1fs: HTTP %s", elapsed, response.status_code)
                raise HTTPException(
                    status_code=502,
                    detail=f"DeepSeek API error ({response.status_code}): {text}",
                )
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                logger.warning("DeepSeek call returned no choices after %.1fs", elapsed)
                raise HTTPException(status_code=502, detail="DeepSeek returned no choices.")
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if content is None:
                logger.warning("DeepSeek call returned empty content after %.1fs", elapsed)
                raise HTTPException(status_code=502, detail="DeepSeek returned empty content.")
            logger.info("DeepSeek call completed in %.1fs", elapsed)
            return str(content)
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        elapsed = time.monotonic() - started
        logger.warning("DeepSeek call raised after %.1fs: %s", elapsed, e)
        raise HTTPException(status_code=502, detail=f"DeepSeek request failed: {e!s}") from e


async def call_llm_api(prompt: str, provider: Optional[str] = None) -> str:

    return await _call_deepseek(prompt)
