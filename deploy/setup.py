"""Genera secretos locales o completa los que faltan al actualizar."""
import argparse
import base64
import json
import os
from pathlib import Path
from secrets import token_bytes, token_urlsafe
from tempfile import NamedTemporaryFile

root = Path(__file__).resolve().parents[1]
path = root / ".env"
parser = argparse.ArgumentParser()
parser.add_argument("--upgrade", action="store_true", help="Añade variables nuevas sin cambiar las existentes")
args = parser.parse_args()
values = {name: token_urlsafe(36) for name in ("POSTGRES_PASSWORD", "APP_PASSWORD", "REPL_PASSWORD", "APP_TOKEN")}
clients = {subject: token_urlsafe(36) for subject in ("demo-alba", "demo-bruno")}
values["CLIENT_TOKENS"] = "'" + json.dumps(clients, separators=(",", ":")) + "'"
values["DATA_KEY"] = base64.urlsafe_b64encode(token_bytes(32)).decode()
values.update(DB_HOST="primary", PORT="8080")

if args.upgrade:
    old = path.read_text(encoding="utf-8")
    keys = {line.split("=", 1)[0].strip() for line in old.splitlines() if "=" in line}
    additions = {key: value for key, value in values.items() if key not in keys}
    if additions:
        with NamedTemporaryFile(mode="w", dir=root, encoding="utf-8", newline="\n", delete=False) as tmp:
            tmp.write(old.rstrip("\n") + "\n")
            for key, value in additions.items():
                tmp.write(f"{key}={value}\n")
        os.replace(tmp.name, path)
else:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit("Ya existe .env. Para completar variables usa --upgrade.")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")
print("Configuración local lista. Usa APP_TOKEN para administración y CLIENT_TOKENS para clientes.")
