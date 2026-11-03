from fastapi import Header, HTTPException

from app.core.firebase import verify_id_token


def current_uid(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return verify_id_token(authorization[7:])["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")