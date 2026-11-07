"""Persistent local accounts and sessions, independent of order storage."""
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import sys
from math import ceil
from contextlib import contextmanager
from time import time

DATABASE = os.getenv("AUTH_DB", "/var/lib/vayxer/auth.sqlite")
ACCOUNTS = {
    "esteban_cliente": ("demo-alba", "cliente"),
    "esteban_admin": ("admin", "admin"),
}


@contextmanager
def store():
    db = sqlite3.connect(DATABASE, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def setup():
    fd = os.open(DATABASE, os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(fd)
    os.chmod(DATABASE, 0o600)
    with store() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                username TEXT PRIMARY KEY, subject TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL, salt BLOB NOT NULL, digest BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                digest TEXT PRIMARY KEY, username TEXT NOT NULL, expires INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiration ON sessions(expires);
            CREATE TABLE IF NOT EXISTS login_failures (
                username TEXT PRIMARY KEY, count INTEGER NOT NULL,
                expires REAL NOT NULL, blocked_until REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS access_events (
                id INTEGER PRIMARY KEY, happened_at REAL NOT NULL,
                action TEXT NOT NULL, username TEXT NOT NULL, actor TEXT NOT NULL
            );
            DROP TABLE IF EXISTS attempts;
        """)
        if "disabled" not in {row["name"] for row in db.execute("PRAGMA table_info(accounts)")}:
            db.execute("ALTER TABLE accounts ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0")


def event(db, action, username, actor="sistema"):
    db.execute("INSERT INTO access_events (happened_at,action,username,actor) VALUES (?,?,?,?)",
               (time(), action, username, actor))
    db.execute("DELETE FROM access_events WHERE id <= (SELECT max(id)-5000 FROM access_events)")


def activity():
    with store() as db:
        events = [dict(row) for row in db.execute(
            "SELECT id,happened_at,action,username,actor FROM access_events ORDER BY id DESC LIMIT 100")]
        clients = [dict(row) for row in db.execute(
            "SELECT username,disabled FROM accounts WHERE role='cliente' ORDER BY username")]
    return {"events": events, "clients": clients}


def set_client_block(username, blocked, actor):
    with store() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT role,disabled FROM accounts WHERE username=?", (username,)).fetchone()
        if row is None:
            raise LookupError("Cuenta no encontrada.")
        if row["role"] != "cliente":
            raise ValueError("Solo se pueden bloquear cuentas cliente.")
        if bool(row["disabled"]) == blocked:
            return
        db.execute("UPDATE accounts SET disabled=? WHERE username=?", (int(blocked),username))
        if blocked:
            db.execute("DELETE FROM sessions WHERE username=?", (username,))
        else:
            db.execute("DELETE FROM login_failures WHERE username=?", (username,))
        event(db, "cuenta_bloqueada" if blocked else "cuenta_desbloqueada", username, actor)


def password_digest(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=3, maxmem=64*1024**2)


def validate_password(password, role):
    symbol = any(not c.isalnum() and not c.isspace() for c in password)
    category = any(c.isalpha() if role == "cliente" else c.isdecimal() for c in password)
    if not (12 <= len(password) <= 128 and symbol and category):
        required = "letras" if role == "cliente" else "números"
        raise ValueError(f"Usa de 12 a 128 caracteres, con {required} y símbolos.")


def provision(username, password, *, only_new=False):
    if not re.fullmatch(r"[a-z0-9_]{3,40}", username):
        raise ValueError("Usuario inválido.")
    subject, role = ACCOUNTS.get(username, (f"account:{username}", "cliente"))
    validate_password(password, role)
    salt = secrets.token_bytes(16)
    digest = password_digest(password, salt)
    with store() as db:
        conflict = "DO NOTHING" if only_new else "DO UPDATE SET salt=excluded.salt, digest=excluded.digest"
        changed = db.execute(
            f"INSERT INTO accounts (username,subject,role,salt,digest) VALUES (?, ?, ?, ?, ?) ON CONFLICT(username) {conflict}",
            (username, subject, role, salt, digest),
        ).rowcount
        if changed:
            event(db, "cuenta_configurada", username, "operador_local")
            db.execute("DELETE FROM sessions WHERE username=?", (username,))
            db.execute("DELETE FROM login_failures WHERE username=?", (username,))
    return bool(changed)


def initial_missing():
    with store() as db:
        existing = {row["username"] for row in db.execute("SELECT username FROM accounts")}
    return [username for username in ACCOUNTS if username not in existing]


def blocked_seconds(db, username, now):
    row = db.execute("SELECT blocked_until FROM login_failures WHERE username=?", (username,)).fetchone()
    return max(0, ceil(row["blocked_until"] - now)) if row else 0


def take_attempt(username):
    now = time()
    with store() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM login_failures WHERE expires<=?", (now,))
        return blocked_seconds(db, username, now)


def failed_attempt(username):
    now = time()
    with store() as db:
        db.execute("BEGIN IMMEDIATE")
        remaining = blocked_seconds(db, username, now)
        if remaining:
            return remaining
        row = db.execute("SELECT count,expires FROM login_failures WHERE username=?", (username,)).fetchone()
        count = 1 + (row["count"] if row and row["expires"] > now else 0)
        event(db, "intento_fallido", username)
        blocked = count >= 3
        db.execute("INSERT OR REPLACE INTO login_failures VALUES (?, ?, ?, ?)",
                   (username, count, now + (5 if blocked else 300), now + 5 if blocked else 0))
        if blocked:
            event(db, "bloqueo_temporal", username)
        return 5 if blocked else 0


def credentials(username, password):
    with store() as db:
        row = db.execute("SELECT salt,digest,disabled FROM accounts WHERE username=?", (username,)).fetchone()
    expected = row["digest"] if row else bytes(64)
    actual = password_digest(password, row["salt"] if row else bytes(16))
    return expected if hmac.compare_digest(expected, actual) and row and not row["disabled"] else None


def session_key(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(username, credential, ttl, previous):
    token = secrets.token_urlsafe(32)
    now = int(time())
    with store() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT digest,disabled FROM accounts WHERE username=?", (username,)).fetchone()
        if not row or row["disabled"] or not hmac.compare_digest(row["digest"], credential) or blocked_seconds(db, username, time()):
            return None
        db.execute("DELETE FROM sessions WHERE expires<=? OR digest=?", (now, session_key(previous)))
        db.execute("DELETE FROM login_failures WHERE username=?", (username,))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (session_key(token), username, now+ttl))
        event(db, "inicio_sesion", username, username)
    return token


def lookup(token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token or ""):
        return None
    with store() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT a.subject,a.role,a.disabled,s.username,s.expires FROM sessions s "
                         "JOIN accounts a ON a.username=s.username WHERE s.digest=?",
                         (session_key(token),)).fetchone()
        if not row:
            return None
        if row["expires"] <= time():
            db.execute("DELETE FROM sessions WHERE digest=?", (session_key(token),))
            event(db, "sesion_expirada", row["username"])
            return None
        if row["disabled"]:
            return None
        return {"subject": row["subject"], "role": row["role"]}


def revoke(token):
    if token:
        with store() as db:
            row = db.execute("SELECT username FROM sessions WHERE digest=?", (session_key(token),)).fetchone()
            if row:
                db.execute("DELETE FROM sessions WHERE digest=?", (session_key(token),))
                event(db, "cierre_sesion", row["username"], row["username"])


def prompt_account(username, *, only_new=False):
    print(f"Cuenta: {username}")
    while True:
        first = getpass.getpass("Contraseña: ")
        if first != getpass.getpass("Confirma la contraseña: "):
            print("Las contraseñas no coinciden.")
            continue
        try:
            if provision(username, first, only_new=only_new):
                print("Cuenta configurada.")
            return
        except ValueError as error:
            print(error)
            if not only_new:
                raise SystemExit(1) from None


if __name__ == "__main__":
    os.umask(0o077)
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python auth_store.py --initial | --needs-setup | USUARIO")
    setup()
    option = sys.argv[1]
    missing = initial_missing()
    if option == "--needs-setup":
        raise SystemExit(3 if missing else 0)
    if not sys.stdin.isatty():
        raise SystemExit("Ejecuta este paso en una terminal interactiva para ocultar la contraseña.")
    if option == "--initial":
        for username in missing:
            prompt_account(username, only_new=True)
    else:
        prompt_account(option)
