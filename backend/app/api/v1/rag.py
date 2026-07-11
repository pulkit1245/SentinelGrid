from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.middlewares.auth_middleware import get_current_user
from app.schemas.auth_schema import UserInToken

router = APIRouter(prefix="/rag")


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    confidence: float


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    body: RAGQueryRequest,
    current_user: Annotated[UserInToken, Depends(get_current_user)],
):
    """Hybrid BM25 + dense retrieval against OISD/DGMS clauses + historical incidents.
    Returns citation-grounded answer.

    NOTE: Full RAG implementation is owned by Member 3 (incident_rag_agent.py).
    This stub returns a placeholder response so the cockpit RAG panel can render.
    """
    # TODO(Member 3): wire to incident_rag_agent.query(body.question)
    return RAGQueryResponse(
        answer=(
            f"[RAG stub] Query received: '{body.question}'. "
            "Member 3's RAG pipeline will replace this with a citation-grounded answer "
            "from the OISD/DGMS corpus."
        ),
        citations=[
            {"source": "OISD Standard 118", "clause": "4.3.2", "excerpt": "Hot-work permits..."},
        ],
        confidence=0.0,
    )
