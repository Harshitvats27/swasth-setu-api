import io

from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1.vector import Vector
from pydantic import BaseModel
from pypdf import PdfReader

from app.core.auth import current_uid
from app.core.firebase import bucket, db
from app.rag.chunking import chunk_text
from app.rag.embedder import embed

router = APIRouter(prefix="/reports")
MAX_BYTES = 10 * 1024 * 1024
MIN_TEXT = 50


class IndexRequest(BaseModel):
    reportId: str


def _set(ref, status: str, message: str = "", **extra):
    ref.update({"status": status, "statusMessage": message, **extra})


def _delete_chunks(uid: str, report_id: str):
    docs = (db.collection("report_chunks")
            .where("uid", "==", uid).where("reportId", "==", report_id).stream())
    batch, n = db.batch(), 0
    for d in docs:
        batch.delete(d.reference)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()


@router.post("/index")
def index_report(req: IndexRequest, uid: str = Depends(current_uid)):
    ref = db.collection("users").document(uid).collection("reports").document(req.reportId)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Report not found")
    data = snap.to_dict()
    path = data.get("storagePath", "")
    if not path.startswith(f"users/{uid}/"):
        raise HTTPException(403, "Invalid path")

    _set(ref, "indexing")
    try:
        blob = bucket.blob(path)
        blob.reload()
        if (blob.size or 0) > MAX_BYTES:
            _set(ref, "unsupported", "File is too large (max 10 MB).")
            return {"status": "unsupported"}
        pdf = blob.download_as_bytes()

        reader = PdfReader(io.BytesIO(pdf))
        if reader.is_encrypted:
            _set(ref, "unsupported", "This PDF is password protected. Please upload an unlocked copy.")
            return {"status": "unsupported"}

        pages = [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
        if sum(len(t.strip()) for _, t in pages) < MIN_TEXT:
            _set(ref, "unsupported",
                 "No text found. This looks like a scanned report. Please upload the original text-based PDF.")
            return {"status": "unsupported"}

        items = []
        for page_no, text in pages:
            for c in chunk_text(text):
                items.append((page_no, c))

        vectors = embed([c for _, c in items])
        _delete_chunks(uid, req.reportId)

        batch = db.batch()
        for n, ((page_no, c), v) in enumerate(zip(items, vectors), start=1):
            batch.set(db.collection("report_chunks").document(), {
                "uid": uid,
                "reportId": req.reportId,
                "title": data.get("title", ""),
                "type": data.get("type", ""),
                "page": page_no,
                "text": c,
                "embedding": Vector(v),
            })
            if n % 400 == 0:
                batch.commit()
                batch = db.batch()
        batch.commit()

        _set(ref, "ready", "", chunkCount=len(items))
        return {"status": "ready", "chunks": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        print("index failed:", repr(e))
        _set(ref, "failed", "Could not process this report. Please try again.")
        return {"status": "failed"}


@router.delete("/{report_id}")
def delete_report(report_id: str, uid: str = Depends(current_uid)):
    ref = db.collection("users").document(uid).collection("reports").document(report_id)
    snap = ref.get()
    if snap.exists:
        path = snap.to_dict().get("storagePath", "")
        if path.startswith(f"users/{uid}/"):
            b = bucket.blob(path)
            if b.exists():
                b.delete()
    _delete_chunks(uid, report_id)
    if snap.exists:
        ref.delete()
    return {"deleted": True}