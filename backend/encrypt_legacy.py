"""Cifra filas antiguas por lotes desde el primario activo."""
from psycopg.types.json import Jsonb

from main import VAULT, connect


def migrate():
    order_count = response_count = 0
    with connect() as db:
        while True:
            with db.transaction():
                orders = db.execute(
                    "SELECT id, customer, item FROM orders WHERE private_payload IS NULL "
                    "LIMIT 100 FOR UPDATE"
                ).fetchall()
                requests = db.execute(
                    "SELECT key, fingerprint, actor, response FROM request_log "
                    "WHERE response IS NOT NULL AND NOT (response ? 'sealed') LIMIT 100 FOR UPDATE"
                ).fetchall()
                for order in orders:
                    payload = VAULT.seal({"customer": order["customer"], "item": order["item"]},
                                         f"order:{order['id']}")
                    db.execute("UPDATE orders SET customer=NULL, item=NULL, private_payload=%s WHERE id=%s",
                               (payload, order["id"]))
                for request in requests:
                    context = f"request:{request['key']}:{request['fingerprint']}:{request['actor']}"
                    db.execute("UPDATE request_log SET response=%s WHERE key=%s",
                               (Jsonb({"sealed": VAULT.seal(request["response"], context)}), request["key"]))
            order_count += len(orders)
            response_count += len(requests)
            if not orders and not requests:
                break
    print(f"Pedidos cifrados: {order_count}. Respuestas cifradas: {response_count}.")


if __name__ == "__main__":
    migrate()
