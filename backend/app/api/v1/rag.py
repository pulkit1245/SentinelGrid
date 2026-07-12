from __future__ import annotations

import logging
import os
import re
import threading

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class RagRequest(BaseModel):
    question: str


router = APIRouter(prefix="/rag", tags=["RAG"])

retriever = None
reranker = None
citation_guard = None
llm = None
_rag_init_lock = threading.Lock()
_rag_init_attempted = False


def _openai_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or settings.LLM_API_KEY or None


def _build_citations(top_chunks: list) -> list[dict]:
    citations = []
    for chunk in top_chunks:
        payload = chunk["payload"]
        text = payload.get("text", "")
        doc_id = payload.get("document_id", "Unknown")
        section_match = re.search(r"Section\s+\d+(?:\.\d+)?|Clause\s+\d+|INC-\d{4}-\d{2}-\d{2}", text, re.I)
        clause = section_match.group(0) if section_match else doc_id
        citations.append({
            "source": doc_id,
            "clause": clause,
            "excerpt": text[:280].strip(),
        })
    return citations


def _extractive_answer(question: str, top_chunks: list) -> dict:
    """Grounded answer from retrieved chunks when no LLM API key is configured."""
    if not top_chunks:
        return {"answer": "I cannot answer based on verified data", "citations": [], "confidence": 0.0}

    citations = _build_citations(top_chunks)
    lead = top_chunks[0]["payload"]["text"].strip()
    answer = (
        f"Based on verified regulatory and incident records in the SentinelGrid knowledge base:\n\n"
        f"{lead}"
    )
    if len(top_chunks) > 1:
        answer += f"\n\nAdditional context: {top_chunks[1]['payload']['text'].strip()[:400]}"
    return {"answer": answer, "citations": citations, "confidence": 0.75}


def init_rag_pipeline() -> bool:
    """Initialize RAG components once (safe to call from startup or first query)."""
    global retriever, reranker, citation_guard, llm, _rag_init_attempted
    with _rag_init_lock:
        if retriever and reranker:
            return True
        if _rag_init_attempted and not retriever:
            return False
        _rag_init_attempted = True
        try:
            from rag.citation_guard import CitationGuard
            from rag.hybrid_retriever import HybridRetriever
            from rag.reranker import ContextReranker

            qdrant_url = os.environ.get("QDRANT_URL", settings.QDRANT_URL)
            qdrant_path = os.environ.get("QDRANT_PATH") or settings.QDRANT_PATH or None
            retriever = HybridRetriever(qdrant_url=qdrant_url, qdrant_path=qdrant_path)
            reranker = ContextReranker()
            citation_guard = CitationGuard()

            api_key = _openai_api_key()
            if api_key:
                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
                logger.info("RAG pipeline initialized with OpenAI LLM")
            else:
                llm = None
                logger.warning("OPENAI_API_KEY / LLM_API_KEY not set — RAG will use extractive retrieval answers")
            logger.info("RAG retriever and reranker ready")
            return True
        except Exception as e:
            logger.error("RAG components failed to initialize: %s", e)
            retriever = None
            reranker = None
            return False


@router.post("/query")
async def query_rag(request: RagRequest):
    """Hybrid retrieval query against OISD/DGMS clauses + historical incidents."""
    if not init_rag_pipeline():
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized (check Qdrant/BM25).")

    from rag.prompts.answer_prompt import build_prompt

    candidates = retriever.search(request.question, top_k=8)
    top_3 = reranker.rerank(request.question, candidates, top_k=3)

    if not top_3:
        return {"answer": "I cannot answer based on verified data", "citations": [], "confidence": 0.0}

    if not llm:
        return _extractive_answer(request.question, top_3)

    max_retries = 1
    for _attempt in range(max_retries + 1):
        prompt = build_prompt(request.question, top_3)
        response = llm.invoke([HumanMessage(content=prompt)])
        answer = response.content

        if citation_guard and citation_guard.verify_citations(answer, top_3):
            return {
                "answer": answer,
                "sources": [chunk["payload"]["document_id"] for chunk in top_3],
                "citations": _build_citations(top_3),
                "confidence": 0.85,
            }

    return {"answer": "I cannot answer based on verified data (failed citation guard)", "citations": []}
