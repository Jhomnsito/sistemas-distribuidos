import hmac
import json
import os
import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class Identity:
    subject: str
    role: str


def credentials():
    clients = json.loads(os.getenv("CLIENT_TOKENS", "{}"))
    if not isinstance(clients, dict):
        raise ValueError("CLIENT_TOKENS debe ser un objeto JSON")
    records = [(Identity("admin", "admin"), os.environ["APP_TOKEN"])]
    for subject, token in clients.items():
        if subject == "admin" or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", subject):
            raise ValueError("Identificador de cliente inválido")
        records.append((Identity(subject, "cliente"), token))
    tokens = [token for _, token in records]
    if any(not isinstance(token, str) or not token.isascii() or len(token) < 32 for token in tokens):
        raise ValueError("Cada token debe tener al menos 32 caracteres ASCII")
    if len(set(tokens)) != len(tokens):
        raise ValueError("Las cuentas deben usar tokens distintos")
    return [(identity, b"Bearer " + token.encode()) for identity, token in records]


ACCOUNTS = credentials()


def authorize(authorization: Annotated[str | None, Header()] = None) -> Identity:
    presented = (authorization or "").encode()
    match = None
    for identity, expected in ACCOUNTS:
        if hmac.compare_digest(presented, expected):
            match = identity
    if match is None:
        raise HTTPException(401, "Clave de acceso incorrecta o ausente", {"WWW-Authenticate": "Bearer"})
    return match


def admin(identity: Annotated[Identity, Depends(authorize)]) -> Identity:
    if identity.role != "admin":
        raise HTTPException(403, "Acceso reservado a administración")
    return identity
