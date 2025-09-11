# scripts/clear_qdrant.py
from qdrant_client import QdrantClient
c = QdrantClient(host="localhost", port=6334, prefer_grpc=True)
if c.collection_exists("chatbi_faqs"):
    c.delete_collection("chatbi_faqs")
print("cleared")