# app/rag/retriever.py
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from .embed import embed_texts
from .reranker import rerank

CANDIDATES = [
    os.getenv("FAQ_COLLECTION") or "",  # prefer explicit if set
    "faqs_v1",
    "faqs",
]


def _client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        prefer_grpc=False,
        timeout=30.0,
    )


def _embed_dim() -> int:
    # embed a tiny probe to get vector length used by the app
    v = embed_texts(["_dim_probe_"])[0]
    return len(v)


def _collection_dim(cli: QdrantClient, name: str) -> Optional[int]:
    try:
        if not cli.collection_exists(name):
            return None
        info = cli.get_collection(name)
        return info.config.params.vectors.size  # type: ignore[attr-defined]
    except Exception:
        return None


def _choose_collection(cli: QdrantClient, wanted_dim: int) -> Optional[str]:
    seen = set()
    for name in CANDIDATES:
        if not name or name in seen:
            continue
        seen.add(name)
        dim = _collection_dim(cli, name)
        if dim == wanted_dim:
            return name
    # if no exact dim match, pick the first existing with points
    for name in CANDIDATES:
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            if cli.collection_exists(name):
                cnt = cli.count(name, exact=True).count  # type: ignore[attr-defined]
                if cnt and cnt > 0:
                    return name
        except Exception:
            pass
    return None


def _build_filter(
    city: Optional[str], category: Optional[str], lang: Optional[str]
) -> Optional[Filter]:
    must = []
    if city:
        city = str(city).strip()
        if city:
            must.append(FieldCondition(key="city", match=MatchValue(value=city)))
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if lang:
        l = str(lang).strip().lower()
        if l:
            must.append(FieldCondition(key="lang", match=MatchValue(value=l)))
    return Filter(must=must) if must else None


def retrieve(
    query: str,
    topk: int = 5,
    city: Optional[str] = None,
    category: Optional[str] = None,
    lang: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not query or not query.strip():
        return []

    cli = _client()
    want = _embed_dim()
    coll = _choose_collection(cli, want) or "faqs_v1"

    vec = embed_texts([query.strip()])[0]
    qfilter = _build_filter(city, category, lang)

    try:
        res = cli.search(
            collection_name=coll, query_vector=vec, limit=topk, query_filter=qfilter
        )
    except Exception as e:
        print(f"[retriever] search failed in {coll}: {e}")
        return []

    hits: List[Dict[str, Any]] = []
    for p in res:
        payload = p.payload or {}
        hits.append(
            {
                "question": payload.get("question"),
                "answer": payload.get("answer"),
                "score": float(p.score),
                "meta": {
                    "id": payload.get("id"),
                    "category": payload.get("category"),
                    "city": payload.get("city"),
                    "lang": payload.get("lang"),
                    "collection": coll,
                },
            }
        )

    return rerank(query, hits, topk=topk)
