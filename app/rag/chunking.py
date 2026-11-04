from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from app.core.firebase import db
from app.rag.embedder import embed

MAX_DISTANCE = 0.65   # test karke tune karo (chhota = zyada strict)


def search_reports(uid: str, query_en: str, k: int = 4, max_distance: float = MAX_DISTANCE) -> list[dict]:
    qvec = embed([query_en])[0]
    docs = (
        db.collection("report_chunks")
        .where(filter=FieldFilter("uid", "==", uid))
        .find_nearest(
            vector_field="embedding",
            query_vector=Vector(qvec),
            distance_measure=DistanceMeasure.COSINE,
            limit=k * 3,
            distance_result_field="distance",
        )
        .stream()
    )
    rows = []
    for d in docs:
        x = d.to_dict()
        dist = x.get("distance")
        if dist is None or dist > max_distance:
            continue
        rows.append({
            "text": x.get("text", ""),
            "title": x.get("title", ""),
            "type": x.get("type", ""),
            "page": x.get("page"),
            "reportId": x.get("reportId", ""),
            "distance": dist,
        })
    rows.sort(key=lambda r: r["distance"])

    seen, out = set(), []
    for r in rows:
        key = " ".join(r["text"].split())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= k:
            break
    return out