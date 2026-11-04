import json
import re
from pathlib import Path

import numpy as np

from app.rag.chunking import chunk_text
from app.rag.embedder import embed

BASE = Path(__file__).parent
KB_DIR = BASE / "kb"
OUT_DIR = BASE / "kb_index"


def parse(text: str) -> tuple[str, str, str]:
    title = re.search(r"^Title:\s*(.+)$", text, re.M)
    source = re.search(r"^Source:\s*(.+)$", text, re.M)
    body = re.sub(r"^(Title|Source):.*$", "", text, flags=re.M).strip()
    return (title.group(1).strip() if title else "", source.group(1).strip() if source else "", body)


def main():
    docs = []
    for f in sorted(KB_DIR.glob("*.txt")):
        title, source, body = parse(f.read_text(encoding="utf-8"))
        for c in chunk_text(body, size=600, overlap_lines=1):
            docs.append({"text": f"{title}\n{c}", "title": title, "source": source, "file": f.name})
    assert docs, "No .txt files found in app/rag/kb/"
    vecs = np.array(embed([d["text"] for d in docs]), dtype="float32")
    OUT_DIR.mkdir(exist_ok=True)
    np.save(OUT_DIR / "vectors.npy", vecs)
    (OUT_DIR / "chunks.json").write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    print(f"Indexed {len(docs)} chunks from {len(set(d['file'] for d in docs))} files")


if __name__ == "__main__":
    main()