from __future__ import annotations
from typing import List, Dict, Any

from .state import GraphState
from ..llm.ollama_client import chat

SYSTEM = (
    "You are Chatbi, a hotel assistant. Keep answers concise and factual. "
    "Follow the user's requested language exactly."
)


def _compose_from_hits(hits: List[Dict[str, Any]]) -> Dict[str, str]:
    if not hits:
        return {"q": "", "a": ""}
    top = hits[0]
    return {
        "q": top.get("question", "").strip(),
        "a": top.get("answer", "").strip(),
    }


def generator_node(state: GraphState) -> GraphState:
    # language from pipeline (e.g., 'it', 'en', 'fr' ...)
    lang = (getattr(state, "lang", None) or "en").strip()
    user = (
        getattr(state, "user_utterance", None) or getattr(state, "user_text", "")
    ).strip()
    hits = getattr(state, "citations", None) or []
    history = (getattr(state, "history", None) or [])[-6:]  # last ~3 turns

    qa = _compose_from_hits(hits)

    if qa["a"]:
        # STRICT translate/rewrite of the FAQ answer into the user's language
        prompt = (
            f"Target language: {lang}\n"
            f"User asked: {user}\n\n"
            f"FAQ answer (English): {qa['a']}\n\n"
            "Task: Translate the FAQ answer into the target language and keep the facts unchanged. "
            "Do not add policy you cannot support. "
            "Respond ONLY in the target language, with 1–2 concise sentences, and no preface."
        )
    else:
        # No FAQ hit → concise fallback in the user's language
        prompt = (
            f"Target language: {lang}\n"
            f"User asked: {user}\n\n"
            "No exact FAQ match was found. Provide a brief, generic hotel-policy answer in the target language. "
            "If the question is out-of-scope, say so briefly. "
            "Respond ONLY in the target language, 1–2 sentences."
        )

    msgs = [{"role": "system", "content": SYSTEM}]
    # add short history (already safe text)
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": prompt})

    try:
        out = chat(msgs)
        # Always set the outward reply to the localized text
        state.reply = (out or "").strip() or getattr(state, "reply", "")
    except Exception:
        # Keep prior reply if LLM fails
        state.reply = (
            getattr(state, "reply", "") or "Sorry, I couldn’t generate an answer."
        )
    return state
