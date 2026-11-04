from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import current_uid
from app.rag.chat import answer

router = APIRouter()


class Msg(BaseModel):
    role: str
    content: str = Field(max_length=500)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[Msg] = Field(default_factory=list, max_length=12)


class Source(BaseModel):
    title: str = ""
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    urgency: str = "routine"
    sources: list[Source] = []
    specialties: list[str] = []


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, uid: str = Depends(current_uid)):
    return answer(uid, req.message, [m.model_dump() for m in req.history])