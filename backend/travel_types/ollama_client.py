import httpx


OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"  


async def call_ollama_api(prompt: str) -> str:
    """Call Ollama API with a prompt."""
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "prompt": prompt,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["response"]
