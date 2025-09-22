from __future__ import annotations
import os
import requests
from typing import List, Dict

BASE = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
MAX_TOK = int(os.getenv("LLM_MAX_TOKENS", "512"))
TEMP = float(os.getenv("LLM_TEMPERATURE", "0.2"))


def chat(messages: List[Dict[str, str]], model: str | None = None) -> str:
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "max_tokens": MAX_TOK,
        "temperature": TEMP,
    }
    r = requests.post(f"{BASE}/chat/completions", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()
