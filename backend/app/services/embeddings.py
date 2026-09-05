from functools import lru_cache

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    vector = _load_model().encode(text, normalize_embeddings=True)
    values = vector.tolist()
    if len(values) != 384:
        raise ValueError(f"Expected a 384-dimensional embedding, received {len(values)} values")
    return [float(value) for value in values]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"