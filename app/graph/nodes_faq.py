from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .state import GraphState
from ..rag.retriever import (
    retrieve,
)  # expects: retrieve(query: str, topk: int, city: Optional[str] = None)

TOPK = int(os.getenv("TOPK", "5"))


def _best_answer(hits: List[Dict[str, Any]]) -> str:
    if not hits:
        return "I couldn't find an answer in FAQs."
    top = hits[0]
    return (
        top.get("answer")
        or top.get("text")
        or top.get("content")
        or "I couldn't find an answer in FAQs."
    )


def _get_query(state: GraphState) -> str:
    # Prefer the common field name; fall back to older names just in case
    return (
        (getattr(state, "user_utterance", None) or "")
        or (getattr(state, "user_text", None) or "")
    ).strip()


def faq_node(state: GraphState) -> GraphState:
    # normalize slots (populates state.city etc.)
    state.normalize()

    q = _get_query(state)
    if not q:
        state.citations = []
        state.answer = "Please ask a question about hotel policies or FAQs."
        return state

    city: Optional[str] = getattr(state, "city", None) or None

    try:
        # Try city + language first
        hits = retrieve(
            query=q, topk=TOPK, city=city, lang=getattr(state, "lang", None)
        )
        # Fallback without city if nothing found
        if not hits:
            hits = retrieve(
                query=q, topk=TOPK, city=None, lang=getattr(state, "lang", None)
            )
        # Final fallback: no language filter
        if not hits:
            hits = retrieve(query=q, topk=TOPK, city=None, lang=None)
    except Exception as e:
        state.citations = []
        state.answer = f"FAQ search failed: {e}"
        return state

    state.citations = hits
    state.answer = _best_answer(hits)
    return state
