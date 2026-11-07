import os
import re
from threading import BoundedSemaphore
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

import auth_store
from security import COOKIE, Identity, is_https, require_origin

router = APIRouter()
ttl = int(os.getenv("SESSION_TTL", "28800"))
if not 1 <= ttl <= 86400:
    raise ValueError("SESSION_TTL debe estar entre 1 y 86400 segundos")
capacity = BoundedSemaphore(2)


class Login(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=40)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


def identity(request: Request):
    user = auth_store.lookup(request.cookies.get(COOKIE))
    if not user:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return Identity(**user)


def admin(identity: Annotated[Identity, Depends(identity)]):
    if identity.role != "admin":
        raise HTTPException(403, "Acceso reservado a administración")
    return identity


def blocked(seconds):
    raise HTTPException(429, f"Demasiados intentos. Vuelve a intentar en {seconds} s.",
                        headers={"Retry-After": str(seconds)})


@router.post("/api/auth/login")
def login(body: Login, request: Request, response: Response):
    require_origin(request)
    if not is_https(request):
        raise HTTPException(403, "El inicio de sesión requiere HTTPS.")
    username = body.username.lower().strip()
    if not re.fullmatch(r"[a-z0-9_]{3,40}", username):
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    if not capacity.acquire(blocking=False):
        raise HTTPException(429, "Demasiados intentos. Vuelve a intentar.")
    try:
        remaining = auth_store.take_attempt(username)
        if remaining:
            blocked(remaining)
        verified = auth_store.credentials(username, body.password)
        if not verified:
            remaining = auth_store.failed_attempt(username)
            if remaining:
                blocked(remaining)
        token = auth_store.new_session(username, verified, ttl, request.cookies.get(COOKIE, "")) if verified else None
    finally:
        capacity.release()
    if not token:
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    response.set_cookie(COOKIE, token, max_age=ttl, httponly=True, secure=is_https(request), samesite="strict")
    return auth_store.lookup(token)


@router.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    require_origin(request)
    auth_store.revoke(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, httponly=True, secure=is_https(request), samesite="strict")


@router.get("/api/auth/session")
@router.get("/internal/session")
def session(user: Annotated[Identity, Depends(identity)]):
    return user


class AccountBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocked: Annotated[bool, Field(strict=True)]


@router.put("/api/auth/accounts/{username}")
def account_block(username: str, body: AccountBlock, request: Request,
                  administrator: Annotated[Identity, Depends(admin)]):
    require_origin(request)
    if not re.fullmatch(r"[a-z0-9_]{3,40}", username):
        raise HTTPException(404, "Cuenta no encontrada.")
    try:
        auth_store.set_client_block(username, body.blocked, administrator.subject)
    except LookupError as error:
        raise HTTPException(404, str(error)) from None
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    return {"username": username, "blocked": body.blocked}
