# scripts/index_to_qdrant.py
import os, csv, hashlib, uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer
import numpy as np

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


COLL = os.getenv("FAQ_COLLECTION", "chatbi_faqs")
BATCH = 256
USE_GRPC = True  # set False if you didn't expose 6334 in compose

client = (
    QdrantClient(host="localhost", port=6334, prefer_grpc=True, timeout=60.0)
    if USE_GRPC
    else QdrantClient(url=QDRANT_URL, timeout=60.0)
)

model = SentenceTransformer(EMBED_MODEL)


def det_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def load_faq_csv(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            q = (r.get("question") or "").strip()
            a = (r.get("answer") or "").strip()
            cat = (r.get("category") or "").strip()
            loc = (r.get("location") or "").strip()
            if not q or not a:
                continue
            text = f"{q} {a}"  # embed Q + A together
            pid = r.get("id") or det_id(text)  # stable id
            rows.append(
                {
                    "id": pid,
                    "type": "faq",
                    "question": q,
                    "answer": a,
                    "category": cat,
                    "location": loc,
                    "text": text,  # the field we embed
                }
            )
    return rows


docs = load_faq_csv("data/chatbi_5000_faqs_clean.csv")
if not docs:
    print("No docs found to index.")
    raise SystemExit(0)

# Create collection if missing
if not client.collection_exists(COLL):
    dim = model.get_sentence_embedding_dimension()
    client.create_collection(
        collection_name=COLL,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
    )


# Embed in batches, normalize for cosine
def embed_batch(texts):
    vec = model.encode(
        texts, convert_to_numpy=True, batch_size=256, show_progress_bar=True
    )
    # L2-normalize
    norms = np.linalg.norm(vec, axis=1, keepdims=True) + 1e-12
    return (vec / norms).astype(np.float32)


# Upsert in batches
for i in range(0, len(docs), BATCH):
    chunk = docs[i : i + BATCH]
    vecs = embed_batch([d["text"] for d in chunk])
    points = [
        qm.PointStruct(id=d["id"], vector=vecs[j], payload=d)
        for j, d in enumerate(chunk)
    ]
    client.upsert(collection_name=COLL, points=points, wait=True)
    print(f"Upserted {i + len(chunk)}/{len(docs)}")

print(f"Indexed {len(docs)} FAQs into {COLL}.")
