import os, json
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from tenacity import retry, stop_after_attempt, wait_fixed
from .embed import embed_texts

COLL  = "faqs_v1"
BATCH = 200
TIMEOUT = 180.0

def get_client():
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
        prefer_grpc=True, grpc_port=6334, timeout=TIMEOUT,
    )

def ensure_collection(c: QdrantClient, dim: int):
    if not c.collection_exists(COLL):
        c.create_collection(
            collection_name=COLL,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                yield json.loads(s)

@retry(wait=wait_fixed(2), stop=stop_after_attempt(5))
def upsert_batch(c: QdrantClient, points: List[PointStruct]):
    c.upsert(collection_name=COLL, points=points)

def run_index(path="data/faqs.jsonl"):
    rows = list(load_jsonl(path))
    if not rows:
        print("No rows in", path); return 0
    qs = [r["question"].strip() for r in rows]
    vecs = embed_texts(qs)
    dim = len(vecs[0])
    c = get_client()
    ensure_collection(c, dim)
    print(f"Indexing {len(rows)} → '{COLL}' in batches of {BATCH}…")
    idx = 0
    for i in range(0, len(rows), BATCH):
        j = min(i+BATCH, len(rows))
        pts = []
        for k in range(i, j):
            r = rows[k]
            payload = {
                "id": r.get("id"),
                "question": r["question"],
                "answer": r["answer"],
                "category": r.get("category"),
                "city": r.get("city") or r.get("location"),
                "lang": r.get("lang", "en"),
            }
            pts.append(PointStruct(id=idx, vector=vecs[k], payload=payload))
            idx += 1
        print(f" • Upserting {len(pts)} [{i}:{j})")
        upsert_batch(c, pts)
    print("Done."); return len(rows)

if __name__ == "__main__":
    run_index()
