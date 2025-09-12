# scripts/index_to_qdrant.py
import os
import json
import argparse
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# Use your project embedder
# - expected: embed_texts(List[str]) -> List[List[float]]
# - located at app/rag/embed.py
from app.rag.embed import embed_texts


def load_jsonl(path: str) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def ensure_collection(client: QdrantClient, coll: str, dim: int):
    if not client.collection_exists(coll):
        client.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def main():
    parser = argparse.ArgumentParser(description="Index FAQs into Qdrant")
    parser.add_argument("--input", default=os.getenv("FAQ_PATH", "/app/data/faqs.jsonl"))
    parser.add_argument("--collection", default=os.getenv("COLL", "faqs_v1"))
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--qdrant", default=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    args = parser.parse_args()

    input_path = args.input
    coll = args.collection
    qdrant_url = args.qdrant

    print(f"[index] reading: {input_path}")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"FAQ file not found: {input_path}")

    docs = load_jsonl(input_path)
    if not docs:
        print("[index] no docs found to index.")
        return

    # Init Qdrant client (HTTP only to avoid gRPC issues in containers)
    client = QdrantClient(url=qdrant_url, prefer_grpc=False, timeout=30.0)

    # Prepare texts to embed (use question; you can concat answer too)
    texts = [d.get("question") or "" for d in docs]
    # Get one vector to know dim
    test_vec = embed_texts([texts[0]])[0]
    dim = len(test_vec)

    ensure_collection(client, coll, dim)
    print(f"[index] collection ready: {coll} (dim={dim})")

    # Embed & upsert in batches
    total = 0
    batch = args.batch
    for i in range(0, len(docs), batch):
        chunk = docs[i : i + batch]
        chunk_texts = [d.get("question", "") for d in chunk]
        vecs = embed_texts(chunk_texts)

        points = []
        for j, (doc, vec) in enumerate(zip(chunk, vecs), start=i):
            # Stable numeric id or fallback
            pid = int(doc.get("id", j + 1))
            payload = {
                "id": str(doc.get("id", pid)),
                "question": doc.get("question"),
                "answer": doc.get("answer"),
                "city": doc.get("city") or doc.get("location"),
                "lang": doc.get("lang", "en"),
                "category": doc.get("category", "faq"),
            }
            points.append(PointStruct(id=pid, vector=vec, payload=payload))

        client.upsert(collection_name=coll, points=points)
        total += len(points)
        print(f"[index] upserted {total}/{len(docs)}")

    # Count
    cnt = client.count(coll, exact=True).count
    print(f"[index] done. collection={coll} count={cnt}")


if __name__ == "__main__":
    main()
