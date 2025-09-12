# app/rag/reranker.py
from typing import List, Dict, Tuple

# Try to use a real cross-encoder. If not available, use a cheap lexical score.
try:
    from sentence_transformers import CrossEncoder

    _CROSS = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2", trust_remote_code=True
    )
except Exception:
    _CROSS = None


def _cheap_score(q: str, text: str) -> float:
    """Very simple overlap score if model not installed."""
    q_tokens = set(q.lower().split())
    d_tokens = set(text.lower().split())
    if not q_tokens:
        return 0.0
    return len(q_tokens & d_tokens) / (len(q_tokens) + 1e-6)


def rerank(query: str, docs: List[Dict], topk: int = 5) -> List[Dict]:
    """
    Re-rank retrieved docs by relevance to `query`.

    docs format:
      [{"question": str, "answer": str, "score": float, "meta": {...}}, ...]

    returns:
      Top-k docs sorted by new score (desc).
    """
    if not docs:
        return []

    pairs = [(query, f"{d.get('question','')} {d.get('answer','')}") for d in docs]

    if _CROSS:
        # Higher score = better
        scores = _CROSS.predict(pairs)
        scored: List[Tuple[float, Dict]] = list(zip(scores, docs))
    else:
        scored = [(_cheap_score(query, text), d) for (_, text), d in zip(pairs, docs)]

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[: max(1, topk)]]
