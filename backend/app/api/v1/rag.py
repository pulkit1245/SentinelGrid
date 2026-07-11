from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from rag.hybrid_retriever import HybridRetriever
from rag.reranker import ContextReranker
from rag.prompts.answer_prompt import build_prompt
from rag.citation_guard import CitationGuard

class RagRequest(BaseModel):
    question: str

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

# Initialize RAG components
retriever = None
reranker = None
citation_guard = None
llm = None 

@router.on_event("startup")
async def startup_event():
    global retriever, reranker, citation_guard, llm
    try:
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        retriever = HybridRetriever(qdrant_url=qdrant_url)
        reranker = ContextReranker()
        citation_guard = CitationGuard()
        
        # Initialize Real LLM
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
        else:
            logging.warning("OPENAI_API_KEY not found. RAG generation will fail.")
            
    except Exception as e:
        logging.error(f"RAG components failed to initialize: {e}")


@router.post("/query")
async def query_rag(request: RagRequest):
    """
    Hybrid retrieval query against OISD/DGMS clauses + historical incidents.
    Returns citation-grounded answer.
    """
    if not retriever or not reranker:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized (check Qdrant/BM25).")

    # 1. Hybrid Retrieval (Top 8)
    candidates = retriever.search(request.question, top_k=8)
    
    # 2. Re-ranking (Top 3)
    top_3 = reranker.rerank(request.question, candidates, top_k=3)
    
    if not top_3:
        return {"answer": "I cannot answer based on verified data"}

    # 3. Generation (with 1 retry loop for hallucination)
    max_retries = 1
    for attempt in range(max_retries + 1):
        prompt = build_prompt(request.question, top_3)
        
        # Call Real LLM
        if not llm:
            raise HTTPException(status_code=500, detail="LLM not configured (missing OPENAI_API_KEY).")
            
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        answer = response.content
        
        # 4. Citation Guard
        if citation_guard.verify_citations(answer, top_3):
            return {
                "answer": answer,
                "sources": [chunk["payload"]["document_id"] for chunk in top_3]
            }
            
    return {"answer": "I cannot answer based on verified data (failed citation guard)"}
