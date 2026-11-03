import numpy as np

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


def embed(texts: list[str]) -> list[list[float]]:
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL)
    out = []
    for v in _model.embed(texts):
        v = np.array(v, dtype="float32")
        out.append((v / np.linalg.norm(v)).tolist())
    return out