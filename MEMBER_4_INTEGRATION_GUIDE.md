# SentinelGrid: Member 4 Integration Guide

This document outlines the components implemented by Member 3 (Knowledge Graph, RAG, Agents) and precisely what needs to be replaced or swapped out during final system integration.

## 1. Environment Variables & LLM Integration
Member 3's backend relies on the OpenAI API to power the RAG and Generation agents. 
*   **What you must do:** Add `OPENAI_API_KEY=sk-...` to the project's `.env` file. 
*   **Location:** The integration is already written in `backend/app/api/v1/rag.py` using `ChatOpenAI`. If the key is missing, those endpoints will throw a 500 error gracefully.

## 2. The Knowledge Graph Database
For rapid local testing without Docker, Member 3 used an in-memory graph (`networkx`).
*   **What you must do:** Swap the import statement from the fallback to the real Neo4j client.
*   **Location:** 
    1.  Open `graph/graph_builder.py` and `backend/app/api/v1/graph.py` and `agents/incident_rag_agent.py` and `agents/compliance_audit_agent.py`.
    2.  Change this line:
        `from graph.networkx_fallback import fallback_graph`
    3.  To this line:
        `from graph.neo4j_client import neo4j_client as fallback_graph` (or rename the variable appropriately).

## 3. Real-Time Event Triggers (Member 1 / 2)
The Knowledge Graph is updated via functions in `graph/graph_builder.py` (e.g., `handle_zone_created`, `handle_permit_issued`).
*   **What you must do:** Hook these functions into your message broker (Kafka/RabbitMQ) or PostgreSQL event listener. Right now, they are passive and waiting to be called.

## 4. PostgreSQL Alerts Database (Member 1)
In the Compliance module, we used a mock dictionary to simulate checking if an alert was confirmed before generating a PDF report.
*   **What you must do:** Replace the `mock_alerts_db` dictionary in `backend/app/api/v1/compliance.py` with the official SQLAlchemy Postgres ORM query built by Member 1.
    *   Change: `alert = mock_alerts_db.get(alert_id)`
    *   To: `alert = db.query(Alert).filter(Alert.id == alert_id).first()`

## 5. Repository Scaffolding
Member 3 generated some files to unblock development (`infra/docker-compose.yml`, `backend/requirements.txt`, `shared/CONTRACTS.md`).
*   **What you must do:** You are free to overwrite or merge these files with Member 1's official versions. Member 3's code only strictly requires the dependencies listed in the `requirements.txt` (FastAPI, Qdrant, LangChain, Neo4j, etc.).
