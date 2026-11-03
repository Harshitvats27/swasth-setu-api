import re


def chunk_text(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}".strip()
        else:
            if cur:
                chunks.append(cur)
            while len(p) > size:
                chunks.append(p[:size])
                p = p[size - overlap:]
            cur = p
    if cur:
        chunks.append(cur)
    return chunks