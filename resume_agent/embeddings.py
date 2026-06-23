from functools import lru_cache

import numpy as np

from resume_agent.config import settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384))
    return _model().encode(texts, normalize_embeddings=True)


def cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (n, d) normalized, b: (m, d) normalized -> (n, m) cosine similarities."""
    if a.shape[0] == 0 or b.shape[0] == 0:
        return np.zeros((a.shape[0], b.shape[0]))
    return a @ b.T


def best_match(query: str, candidates: list[str]) -> tuple[str | None, float]:
    """Return (best matching candidate, similarity) for a single query string."""
    if not candidates:
        return None, 0.0
    q = embed([query])
    c = embed(candidates)
    sims = cosine_sim_matrix(q, c)[0]
    idx = int(np.argmax(sims))
    return candidates[idx], float(sims[idx])
