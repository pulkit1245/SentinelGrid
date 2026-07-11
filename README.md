# SentinelGrid

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

SentinelGrid is a compound-risk detection platform designed for heavy industry. It monitors multiple zones for environmental, physical, and operational hazards in real-time, aggregating events from various sources (sensors, cameras, access control) into a unified Plant Risk Graph to uncover hidden risks, like an active hot-work permit overlapping with an unexpected gas leak.

## Architecture

Built by a 3-member team for a hackathon:
- **Member 1**: Core platform (APIs, UI Cockpit, real-time sync, auth).
- **Member 2**: Agents, Simulator, ML/CV event ingestion.
- **Member 3**: Plant Risk Graph (Neo4j), RAG compliance querying.

### Tech Stack
| Component | Technology |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Frontend | React, TypeScript, Vite |
| Databases | PostgreSQL (TimescaleDB), Neo4j, Redis, Qdrant |
| Integration | WebSockets, REST |

## Quick Start

1. Start infrastructure:
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```
2. Set up backend:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   python -m scripts.seed_live_data
   uvicorn app.main:app --reload
   ```
3. Set up frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Demo Credentials
- Plant Admin: `admin@sentinelgrid.demo` / `Demo@1234`
- Safety Officer: `officer@sentinelgrid.demo` / `Demo@1234`

## Folder Structure
```
SentinelGrid/
├── backend/      # FastAPI backend
├── frontend/     # React frontend
├── infra/        # Docker Compose and CI/CD
├── shared/       # Shared event schemas and contracts
├── agents/       # AI agents (M2/M3)
├── cv/           # Computer Vision pipelines (M2)
├── rag/          # RAG service (M3)
├── graph/        # Graph builder and queries (M3)
└── simulator/    # Synthetic event generator (M2)
```
