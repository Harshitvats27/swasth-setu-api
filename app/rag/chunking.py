import re


def chunk_text(text: str, size: int = 600, overlap_lines: int = 2) -> list[str]:
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if l]

    parts = []
    for l in lines:
        while len(l) > size:
            cut = l.rfind(" ", 0, size)
            if cut <= 0:
                cut = size
            parts.append(l[:cut].strip())
            l = l[cut:].strip()
        if l:
            parts.append(l)

    chunks, cur, cur_len = [], [], 0
    for p in parts:
        if cur and cur_len + len(p) + 1 > size:
            chunks.append("\n".join(cur))
            tail = cur[-overlap_lines:]
            while tail and sum(len(x) + 1 for x in tail) > size // 3:
                tail = tail[1:]
            cur = list(tail)
            cur_len = sum(len(x) + 1 for x in cur)
        cur.append(p)
        cur_len += len(p) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks