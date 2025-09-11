# app/rag/retriever.py
import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from .embed import embed_texts

COLL = "faqs_v1"  # <- MUST match what you indexed


def retrieve(
    query: str, topk: int = 5, city: str | None = None, category: str | None = None
):
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        prefer_grpc=True,
        grpc_port=6334,
        timeout=30.0,
    )
    vec = embed_texts([query])[0]

    qfilter = None
    must = []
    if city:
        must.append(FieldCondition(key="city", match=MatchValue(value=city)))
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if must:
        qfilter = Filter(must=must)

    # Defensive: if the collection doesn't exist, return empty hits instead of crashing
    try:
        res = client.search(
            collection_name=COLL, query_vector=vec, limit=topk, query_filter=qfilter
        )
    except Exception as e:
        # log this in real code; for now just fail-soft
        return []

    hits = []
    for p in res:
        payload = p.payload or {}
        hits.append(
            {
                "question": payload.get("question"),
                "answer": payload.get("answer"),
                "score": float(p.score),
                "meta": {k: payload.get(k) for k in ("id", "category", "city", "lang")},
            }
        )
    return hits
