import asyncio
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, closing, suppress
from datetime import datetime, timezone
from threading import Lock
from urllib.request import urlopen

import psycopg
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row

import auth_store
from auth_routes import admin, router

HISTORY = os.getenv("MONITOR_DB", "/var/lib/vayxer/health.sqlite")
SERVICES = {
    "gateway": os.getenv("GATEWAY_PROBE", "http://gateway/"),
    "api-a": os.getenv("API_A_PROBE", "http://api-a:8000"),
    "api-b": os.getenv("API_B_PROBE", "http://api-b:8000"),
    "primario": None,
    "replica": None,
}


def store():
    db = sqlite3.connect(HISTORY, timeout=3)
    db.row_factory = sqlite3.Row
    return db


def setup():
    with closing(store()) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS health (
                service TEXT PRIMARY KEY, state TEXT NOT NULL, checked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, service TEXT NOT NULL, previous TEXT,
                state TEXT NOT NULL, happened_at TEXT NOT NULL
            );
        """)


def probe_http(url):
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def postgres(**kwargs):
    return psycopg.connect(connect_timeout=2, options="-c statement_timeout=2000", **kwargs)


def probe(service):
    try:
        if service == "primario":
            with postgres(target_session_attrs="read-write") as db:
                db.execute("SELECT 1").fetchone()
            return "operativo"
        if service == "replica":
            with postgres(host=os.getenv("REPLICA_HOST", "replica"),
                          port=os.getenv("REPLICA_PORT", "5432")) as db:
                recovery, receiving = db.execute(
                    "SELECT pg_is_in_recovery(), EXISTS (SELECT 1 FROM pg_stat_wal_receiver)"
                ).fetchone()
            return "operativo" if recovery and receiving else "degradado"
        url = SERVICES[service]
        if service == "gateway":
            return "operativo" if probe_http(url) else "caido"
        if not probe_http(url + "/api/live"):
            return "caido"
        return "operativo" if probe_http(url + "/api/ready") else "degradado"
    except psycopg.Error:
        return "caido"


def sample():
    with ThreadPoolExecutor(len(SERVICES)) as pool:
        states = dict(zip(SERVICES, pool.map(probe, SERVICES)))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(store()) as db, db:
        for service, state in states.items():
            row = db.execute("SELECT state FROM health WHERE service=?", (service,)).fetchone()
            old = row["state"] if row else None
            if old != state:
                db.execute(
                    "INSERT INTO events (service, previous, state, happened_at) VALUES (?, ?, ?, ?)",
                    (service, old, state, now),
                )
            db.execute(
                "INSERT INTO health VALUES (?, ?, ?) ON CONFLICT(service) DO UPDATE "
                "SET state=excluded.state, checked_at=excluded.checked_at", (service, state, now),
            )


async def watch():
    while True:
        try:
            await asyncio.to_thread(sample)
        except sqlite3.Error:
            import logging
            logging.getLogger("uvicorn.error").warning("No se pudo escribir el historial de salud")
        await asyncio.sleep(4)


@asynccontextmanager
async def lifespan(_app):
    setup()
    auth_store.setup()
    observer = asyncio.create_task(watch())
    try:
        yield
    finally:
        observer.cancel()
        with suppress(asyncio.CancelledError):
            await observer


app = FastAPI(title="Vayxer · Operaciones", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _error):
    return JSONResponse(status_code=422, content={"detail": "Solicitud inválida."})


audit_pool = ThreadPoolExecutor(max_workers=1)
audit_lock = Lock()
audit_query = None


def read_audit():
    try:
        with postgres(target_session_attrs="read-write", row_factory=dict_row) as db:
            order_events = db.execute(
                "SELECT happened_at, action, from_status, to_status, actor_role "
                "FROM order_audit ORDER BY happened_at DESC LIMIT 60"
            ).fetchall()
        audit_available = True
    except psycopg.Error:
        order_events, audit_available = [], False
    return order_events, audit_available


def audit_with_deadline():
    global audit_query
    with audit_lock:
        if audit_query is None or audit_query.done():
            audit_query = audit_pool.submit(read_audit)
        pending = audit_query
    try:
        return pending.result(timeout=1.5)
    except TimeoutError:
        # Limita la espera HTTP aun si DNS o la conexión tardan más.
        return [], False


@app.get("/api/ops/summary", dependencies=[Depends(admin)])
def summary():
    with closing(store()) as db:
        states = [dict(row) for row in db.execute("SELECT * FROM health ORDER BY service")]
        events = [dict(row) for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 60")]
    order_events, audit_available = audit_with_deadline()
    return {"access": auth_store.activity(), "services": states, "events": events, "orders": order_events,
            "audit_available": audit_available}


@app.middleware("http")
async def no_cache(request, call_next):
    try:
        response = await call_next(request)
    except sqlite3.Error:
        response = JSONResponse(status_code=503, content={"detail": "Historial no disponible"})
    response.headers["Cache-Control"] = "no-store"
    return response
