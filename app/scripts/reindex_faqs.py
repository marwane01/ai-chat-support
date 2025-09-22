import os, json, sys, math
from pathlib import Path
from typing import List, Dict, Any

# --- Embeddings (uses your multilingual model default) ---
from app.rag.embed import embed_texts

# --- Choose backend: QDRANT or PGVECTOR ---
BACKEND = os.getenv("FAQ_BACKEND", "QDRANT").upper()

# ---- Input: JSONL of FAQs (one per line)
# expected keys: id, hotel_id, city, lang, question, answer, tags (optional)
FAQ_JSONL = os.getenv("FAQ_JSONL", "data/faqs.jsonl")

BATCH = int(os.getenv("BATCH", "256"))
DRY = os.getenv("DRY_RUN", "false").lower() == "true"


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            out.append(json.loads(line))
    return out


# ---------------- QDRANT backend ----------------
def upsert_qdrant(items: List[Dict[str, Any]]):
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qm

    url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    collection = os.getenv("FAQ_COLLECTION", "faqs")
    client = QdrantClient(url=url)

    # Create collection if missing (cosine, 768/1024 depending on model; we infer from first vector)
    vec = embed_texts(["probe"])[0]
    dim = len(vec)

    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing and not DRY:
        client.recreate_collection(
            collection_name=collection,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )

    # Upsert in batches
    total = len(items)
    for i in range(0, total, BATCH):
        chunk = items[i : i + BATCH]
        vectors = embed_texts([it["question"] for it in chunk])
        points = []
        for it, v in zip(chunk, vectors):
            points.append(
                qm.PointStruct(
                    id=it["id"],
                    vector=v,
                    payload={
                        "hotel_id": it.get("hotel_id"),
                        "city": it.get("city"),
                        "lang": it.get("lang", "en"),
                        "question": it.get("question"),
                        "answer": it.get("answer"),
                        "tags": it.get("tags", []),
                    },
                )
            )
        if not DRY:
            client.upsert(collection_name=collection, points=points)
        print(f"[QDRANT] Upserted {min(i+BATCH, total)}/{total}")
    print("[QDRANT] Done.")


# ---------------- PGVECTOR backend ----------------
def upsert_pgvector(items: List[Dict[str, Any]]):
    # Requires: pip install psycopg[binary] pgvector
    from sqlalchemy import create_engine, text

    dsn = (
        os.getenv("POSTGRES_DSN")
        or os.getenv("DATABASE_URL")
        or "postgresql+psycopg://chatbi:chatbi@postgres:5432/chatbi"
    )
    engine = create_engine(dsn)

    # Infer embedding dim
    dim = len(embed_texts(["probe"])[0])

    schema_sql = f"""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS faqs (
        id TEXT PRIMARY KEY,
        hotel_id INT,
        city TEXT,
        lang TEXT,
        question TEXT,
        answer TEXT,
        tags JSONB
    );

    -- vector table for embeddings
    CREATE TABLE IF NOT EXISTS faqs_vec (
        id TEXT PRIMARY KEY REFERENCES faqs(id) ON DELETE CASCADE,
        embedding vector({dim})
    );

    CREATE INDEX IF NOT EXISTS faqs_vec_idx ON faqs_vec
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

    """
    with engine.begin() as conn:
        if not DRY:
            for stmt in schema_sql.strip().split(";\n\n"):
                if stmt.strip():
                    conn.execute(text(stmt))

        total = len(items)
        for i in range(0, total, BATCH):
            chunk = items[i : i + BATCH]
            vecs = embed_texts([it["question"] for it in chunk])

            # upsert metadata
            if not DRY:
                conn.execute(
                    text(
                        """
                    INSERT INTO faqs (id, hotel_id, city, lang, question, answer, tags)
                    VALUES (:id, :hotel_id, :city, :lang, :question, :answer, CAST(:tags AS JSONB))
                    ON CONFLICT (id) DO UPDATE SET
                        hotel_id=EXCLUDED.hotel_id,
                        city=EXCLUDED.city,
                        lang=EXCLUDED.lang,
                        question=EXCLUDED.question,
                        answer=EXCLUDED.answer,
                        tags=EXCLUDED.tags
                    """
                    ),
                    [
                        {
                            "id": it["id"],
                            "hotel_id": it.get("hotel_id"),
                            "city": it.get("city"),
                            "lang": it.get("lang", "en"),
                            "question": it.get("question"),
                            "answer": it.get("answer"),
                            "tags": json.dumps(it.get("tags", [])),
                        }
                        for it in chunk
                    ],
                )

                # upsert vectors
                conn.execute(
                    text(
                        f"""
                    INSERT INTO faqs_vec (id, embedding)
                    VALUES (:id, :embedding)
                    ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding
                    """
                    ),
                    [
                        {"id": it["id"], "embedding": vec}
                        for it, vec in zip(chunk, vecs)
                    ],
                )
            print(f"[PGVECTOR] Upserted {min(i+BATCH, total)}/{total}")
    print("[PGVECTOR] Done.")


def main():
    path = Path(FAQ_JSONL)
    if not path.exists():
        print(f"Input not found: {path}", file=sys.stderr)
        sys.exit(1)

    items = load_jsonl(str(path))
    if not items:
        print("No items to index.")
        return

    print(f"Loaded {len(items)} FAQs from {FAQ_JSONL}")
    print(f"Backend: {BACKEND} | Dry-run: {DRY} | Batch: {BATCH}")

    if BACKEND == "QDRANT":
        upsert_qdrant(items)
    elif BACKEND == "PGVECTOR":
        upsert_pgvector(items)
    else:
        print("Set FAQ_BACKEND=QDRANT or PGVECTOR", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
