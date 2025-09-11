from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import numpy as np

client = QdrantClient(host="localhost", port=6334, prefer_grpc=True)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

q = "Is breakfast included at Chatbi Paris?"
v = model.encode([q], convert_to_numpy=True)
v = (v / (np.linalg.norm(v, axis=1, keepdims=True)+1e-12)).astype(np.float32)[0]
hits = client.search(collection_name="chatbi_faqs", query_vector=v, limit=3)
for h in hits:
    p = h.payload
    print(round(h.score,4), "-", p.get("question"), "->", p.get("answer"))
