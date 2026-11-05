import hmac
import logging
import os
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

import psycopg
from cryptography.exceptions import InvalidTag
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from domain import OrderDelete, OrderFields, OrderUpdate, Status, can_transition, fingerprint
from security import Identity, admin, authorize
from vault import Vault

NODE = os.getenv("NODE_ID", "api-local")
VAULT = Vault(os.environ["DATA_KEY"])
log = logging.getLogger("uvicorn.error")
app = FastAPI(title="Vayxer · Gestión de pedidos", docs_url=None, redoc_url=None, openapi_url=None)
Actor = Annotated[Identity, Depends(authorize)]
Admin = Annotated[Identity, Depends(admin)]
Key = Annotated[UUID, Header(alias="Idempotency-Key")]


@app.middleware("http")
async def observe(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Node-ID"] = NODE
    response.headers["Cache-Control"] = "no-store"
    route = getattr(request.scope.get("route"), "path", "unmatched")
    log.info("node=%s method=%s route=%s status=%s ms=%.2f",
             NODE, request.method, route, response.status_code, (perf_counter() - started) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, error):
    fields = [".".join(map(str, item["loc"])) for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": "Solicitud inválida", "fields": fields})


@app.exception_handler(psycopg.Error)
@app.exception_handler(InvalidTag)
async def unavailable(_request, error):
    log.warning("node=%s storage_error=%s", NODE, type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "Datos no disponibles. Reintenta."})


def connect():
    return psycopg.connect(
        connect_timeout=2, row_factory=dict_row, target_session_attrs="read-write",
        options="-c statement_timeout=3000 -c lock_timeout=2000",
    )


def public_order(row):
    row.pop("owner_id")
    payload = row.pop("private_payload")
    if payload is not None:
        row.update(VAULT.open(payload, f"order:{row['id']}"))
    return row


@app.get("/api/live")
def live():
    return {"status": "alive", "node": NODE}


@app.get("/api/ready")
def ready():
    with connect() as db:
        db.execute("SELECT private_payload FROM orders LIMIT 1").fetchone()
        db.execute("SELECT actor FROM request_log LIMIT 1").fetchone()
        db.execute("SELECT event_id FROM order_audit LIMIT 1").fetchone()
    return {"status": "ready", "node": NODE}


@app.get("/api/session")
def session(identity: Actor):
    return identity


@app.get("/api/orders")
def list_orders(identity: Actor, limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or not 0 <= offset <= 1000000:
        raise HTTPException(422, "Paginación inválida")
    predicate = "" if identity.role == "admin" else "WHERE owner_id = %s "
    args = () if identity.role == "admin" else (identity.subject,)
    with connect() as db:
        rows = db.execute("SELECT * FROM orders " + predicate +
                          "ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
                          (*args, limit, offset)).fetchall()
    return [public_order(row) for row in rows]


@app.get("/api/orders/{order_id}")
def get_order(order_id: UUID, identity: Actor):
    predicate = "" if identity.role == "admin" else " AND owner_id = %s"
    args = (order_id,) if identity.role == "admin" else (order_id, identity.subject)
    with connect() as db:
        row = db.execute("SELECT * FROM orders WHERE id = %s" + predicate, args).fetchone()
    if row is None:
        raise HTTPException(404, "Pedido no encontrado")
    return public_order(row)


def mutate(method, order_id, data, key, identity, action):
    legacy_signature = fingerprint(method, str(order_id), data)
    signature = VAULT.fingerprint(legacy_signature)
    context = f"request:{key}:{signature}:{identity.subject}"
    with connect() as db:
        claimed = db.execute(
            "INSERT INTO request_log (key, fingerprint, actor) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING RETURNING key", (key, signature, identity.subject),
        ).fetchone()
        if claimed is None:
            previous = db.execute(
                "SELECT fingerprint, actor, response FROM request_log WHERE key = %s", (key,),
            ).fetchone()
            stored_signature = previous["fingerprint"]
            expected = signature if stored_signature.startswith("v1.") else legacy_signature
            if not hmac.compare_digest(stored_signature, expected) or previous["actor"] != identity.subject:
                raise HTTPException(409, "La clave de idempotencia ya pertenece a otra solicitud")
            response = previous["response"]
            if "sealed" not in response:
                return response
            return VAULT.open(response["sealed"], f"request:{key}:{stored_signature}:{identity.subject}")
        result = jsonable_encoder(action(db))
        db.execute("UPDATE request_log SET response = %s WHERE key = %s",
                   (Jsonb({"sealed": VAULT.seal(result, context)}), key))
        return result


def lock_order(db, order_id, version):
    current = db.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (order_id,)).fetchone()
    if current is None:
        raise HTTPException(404, "Pedido no encontrado")
    if current["version"] != version:
        raise HTTPException(409, "Otro operador modificó este pedido. Actualiza la lista.")
    return current


def audit(db, action, identity, before, after):
    db.execute(
        "INSERT INTO order_audit (event_id, action, actor_role, from_status, to_status) "
        "VALUES (%s, %s, %s, %s, %s)", (uuid4(), action, identity.role, before, after),
    )


def seal_fields(data, order_id):
    return VAULT.seal({"customer": data.customer, "item": data.item}, f"order:{order_id}")


@app.post("/api/orders", status_code=201)
def create(data: OrderFields, key: Key, identity: Actor):
    def insert(db):
        order_id = uuid4()
        owner = identity.subject if identity.role == "cliente" else None
        row = db.execute(
            "INSERT INTO orders (id, private_payload, owner_id, quantity, status) "
            "VALUES (%s, %s, %s, %s, 'pendiente') RETURNING *",
            (order_id, seal_fields(data, order_id), owner, data.quantity),
        ).fetchone()
        audit(db, "creado", identity, None, row["status"])
        return public_order(row)
    return mutate("POST", None, data, key, identity, insert)


@app.put("/api/orders/{order_id}")
def update(order_id: UUID, data: OrderUpdate, key: Key, identity: Admin):
    def replace(db):
        current = lock_order(db, order_id, data.version)
        if not can_transition(Status(current["status"]), data.status):
            raise HTTPException(409, "El estado solo puede avanzar un paso")
        row = db.execute(
            "UPDATE orders SET customer=NULL, item=NULL, private_payload=%s, quantity=%s, status=%s, "
            "version=version+1, updated_at=clock_timestamp() WHERE id=%s RETURNING *",
            (seal_fields(data, order_id), data.quantity, data.status.value, order_id),
        ).fetchone()
        action = "editado" if current["status"] == row["status"] else "estado"
        audit(db, action, identity, current["status"], row["status"])
        return public_order(row)
    return mutate("PUT", order_id, data, key, identity, replace)


@app.delete("/api/orders/{order_id}")
def delete(order_id: UUID, data: OrderDelete, key: Key, identity: Admin):
    def remove(db):
        current = lock_order(db, order_id, data.version)
        db.execute("DELETE FROM orders WHERE id=%s", (order_id,))
        audit(db, "eliminado", identity, current["status"], None)
        return {"id": order_id, "deleted": True}
    return mutate("DELETE", order_id, data, key, identity, remove)
