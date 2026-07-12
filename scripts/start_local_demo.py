#!/usr/bin/env python3
"""Start SentinelGrid locally without Docker (Windows-friendly demo launcher)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
LOCAL = ROOT / ".local"
PGDATA = LOCAL / "pgdata"
REDIS_EXE = Path(r"C:\Program Files\Redis\redis-server.exe")


def start_postgres() -> tuple[str, str]:
    import pgembed

    PGDATA.mkdir(parents=True, exist_ok=True)
    server = pgembed.get_server(str(PGDATA))
    uri = server.get_uri()
    async_url = uri.replace("postgresql://", "postgresql+asyncpg://", 1)
    sync_url = uri
    return async_url, sync_url


def start_redis() -> subprocess.Popen | None:
    if not REDIS_EXE.exists():
        print("⚠ Redis not found — ingest streams will log warnings only.")
        return None
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sock.connect_ex(("127.0.0.1", 6379)) == 0:
            sock.close()
            print("✓ Redis already running on :6379")
            return None
        sock.close()
    except OSError:
        pass
    proc = subprocess.Popen(
        [str(REDIS_EXE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    time.sleep(1.5)
    print("✓ Redis started on :6379")
    return proc


def run_migrations(sync_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_SYNC_URL"] = sync_url
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        check=True,
    )
    print("✓ Database migrations applied")


def run_seed(async_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = async_url
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [sys.executable, "-m", "scripts.seed_demo_data"],
        cwd=BACKEND,
        env=env,
        check=True,
    )


def write_env(async_url: str, sync_url: str) -> None:
    qdrant_path = str(LOCAL / "qdrant").replace("\\", "/")
    content = f"""DATABASE_URL={async_url}
DATABASE_SYNC_URL={sync_url}
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=dev-secret-change-in-production
SERVICE_TOKEN=dev-service-token
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
QDRANT_URL=http://localhost:6333
QDRANT_PATH={qdrant_path}
"""
    for path in (ROOT / ".env", BACKEND / ".env"):
        path.write_text(content, encoding="utf-8")
    print(f"✓ Wrote {ROOT / '.env'}")


def launch_process(name: str, cmd: list[str], cwd: Path, extra_env: dict | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    if extra_env:
        env.update(extra_env)
    print(f"→ Starting {name}...")
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def main() -> None:
    print("=" * 60)
    print("SentinelGrid — Local Demo Launcher")
    print("=" * 60)

    async_url, sync_url = start_postgres()
    print(f"✓ Embedded PostgreSQL: {sync_url}")

    redis_proc = start_redis()
    write_env(async_url, sync_url)

    try:
        run_migrations(sync_url)
        run_seed(async_url)
    except subprocess.CalledProcessError as exc:
        print(f"✗ Setup failed: {exc}")
        sys.exit(1)

    backend_env = {
        "DATABASE_URL": async_url,
        "DATABASE_SYNC_URL": sync_url,
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_SECRET_KEY": "dev-secret-change-in-production",
        "SERVICE_TOKEN": "dev-service-token",
        "ENVIRONMENT": "development",
        "QDRANT_PATH": str(LOCAL / "qdrant"),
    }

    procs: list[tuple[str, subprocess.Popen]] = []

    procs.append(
        (
            "backend",
            launch_process(
                "API (http://localhost:8000)",
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                BACKEND,
                backend_env,
            ),
        )
    )

    procs.append(
        (
            "frontend",
            launch_process(
                "Frontend (http://localhost:5173)",
                ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
                FRONTEND,
            ),
        )
    )

    procs.append(
        (
            "enrichment",
            launch_process(
                "Enrichment worker",
                [sys.executable, "-m", "app.workers.tasks.enrichment_task"],
                BACKEND,
                backend_env,
            ),
        )
    )

    procs.append(
        (
            "simulator",
            launch_process(
                "Plant simulator (compound-risk scenario)",
                [
                    sys.executable,
                    "-m",
                    "simulator.plant_simulator",
                    "--scenario",
                    "compound_risk_1",
                    "--speed",
                    "120",
                    "--base-url",
                    "http://localhost:8000",
                ],
                ROOT,
                {"SENTINELGRID_SERVICE_TOKEN": "dev-service-token", "SERVICE_TOKEN": "dev-service-token"},
            ),
        )
    )

    print()
    print("=" * 60)
    print("Demo is running!")
    print("  Cockpit:  http://localhost:5173")
    print("  API docs: http://localhost:8000/docs")
    print("  Login:    admin@sentinelgrid.demo / Demo@1234")
    print("=" * 60)
    print("Press Ctrl+C to stop all services.")
    print()

    try:
        while True:
            time.sleep(2)
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"⚠ Process '{name}' exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\nStopping services...")
        for name, proc in procs:
            proc.terminate()
        if redis_proc:
            redis_proc.terminate()
        print("Done.")


if __name__ == "__main__":
    main()
