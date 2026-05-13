import os
from typing import Optional

import httpx
from fastapi import HTTPException

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

ALLOWED = frozenset({"deepseek", "ollama"})


def normalize_llm_provider(value: Optional[str]) -> str:
    if not value:
        return "deepseek"
    v = str(value).strip().lower()
    return v if v in ALLOWED else "deepseek"


async def _call_ollama(prompt: str) -> str:
    payload = {"model": OLLAMA_MODEL, "stream": False, "prompt": prompt}
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response") or ""
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Local Ollama request failed: {e!s}. Is Ollama running?",
        ) from e


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
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                text = response.text[:500]
                raise HTTPException(
                    status_code=502,
                    detail=f"DeepSeek API error ({response.status_code}): {text}",
                )
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise HTTPException(status_code=502, detail="DeepSeek returned no choices.")
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if content is None:
                raise HTTPException(status_code=502, detail="DeepSeek returned empty content.")
            return str(content)
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"DeepSeek request failed: {e!s}") from e


async def call_llm_api(prompt: str, provider: Optional[str] = None) -> str:
    """Run the travel-planning prompt on DeepSeek (cloud) or local Ollama."""
    p = normalize_llm_provider(provider or os.getenv("DEFAULT_LLM_PROVIDER"))
    if p == "ollama":
        return await _call_ollama(prompt)
    return await _call_deepseek(prompt)
