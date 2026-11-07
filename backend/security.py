import json
import re
from dataclasses import dataclass
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, HTTPException, Request as IncomingRequest

COOKIE = "vayxer_session"


@dataclass(frozen=True)
class Identity:
    subject: str
    role: str


def is_https(request):
    return request.headers.get("x-forwarded-proto") == "https"


def require_origin(request):
    origin = request.headers.get("origin")
    scheme = "https" if is_https(request) else "http"
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and origin != f"{scheme}://{request.headers['host']}"
    ):
        raise HTTPException(403, "Origen no permitido.")


def authorize(request: IncomingRequest) -> Identity:
    token = request.cookies.get(COOKIE)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        require_origin(request)
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token or ""):
        raise HTTPException(401, "Inicia sesión para continuar.")
    query = Request("http://monitor:8000/internal/session", headers={"Cookie": f"{COOKIE}={token}"})
    try:
        with urlopen(query, timeout=2) as result:
            return Identity(**json.load(result))
    except HTTPError as error:
        if error.code == 401:
            raise HTTPException(401, "Tu sesión no está activa.") from error
        raise HTTPException(503, "Autenticación temporalmente no disponible.") from error
    except (URLError, TimeoutError) as error:
        raise HTTPException(503, "Autenticación temporalmente no disponible.") from error


def admin(identity: Annotated[Identity, Depends(authorize)]) -> Identity:
    if identity.role != "admin":
        raise HTTPException(403, "Acceso reservado a administración")
    return identity
