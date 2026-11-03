from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.search.rules import rule_urgency
from app.search.understand import understand_query

router = APIRouter()
RANK = {"routine": 0, "urgent": 1, "emergency": 2}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class SearchResponse(BaseModel):
    specializations: list[str]
    urgency: Literal["routine", "urgent", "emergency"]
    symptoms_en: list[str]
    fallback: bool = False


@router.post("/search/understand", response_model=SearchResponse)
def understand(req: SearchRequest):
    rule = rule_urgency(req.query)
    info = understand_query(req.query)
    if info is None:   # LLM failed: the rules still protect the user
        return SearchResponse(specializations=[], urgency=rule or "routine",
                              symptoms_en=[], fallback=True)
    urgency = max(info["urgency"], rule or "routine", key=RANK.get)
    return SearchResponse(**{**info, "urgency": urgency})