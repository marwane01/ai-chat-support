import os
from sentence_transformers import SentenceTransformer

_model = None


def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer(
            os.getenv(
                "EMBED_MODEL",
                "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
            )
        )
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()
