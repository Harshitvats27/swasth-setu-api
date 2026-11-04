import json
from pathlib import Path

import numpy as np

from app.rag.embedder import embed

INDEX_DIR = Path(__file__).parent / "kb_index"
_vecs = None
_chunks = None


def _load():
    global _vecs, _chunks
    if _vecs is None:
        _vecs = np.load(INDEX_DIR / "vectors.npy")
        _chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))


def search_kb(query_en: str, k: int = 3, max_distance: float = 0.6) -> list[dict]:
    _load()
    q = np.array(embed([query_en])[0], dtype="float32")
    sims = _vecs @ q
    out = []
    for i in np.argsort(-sims)[: k * 2]:
        dist = 1.0 - float(sims[i])
        if dist > max_distance:
            continue
        out.append({**_chunks[i], "distance": dist})
        if len(out) >= k:
            break
    return out