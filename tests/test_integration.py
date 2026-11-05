import json
import os
import subprocess
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


TOKEN = os.environ["APP_TOKEN"]
CLIENTS = json.loads(os.environ["CLIENT_TOKENS"])
URL = os.getenv("TEST_URL", "http://127.0.0.1:8080")
FIELDS = {"customer": "Prueba automática", "item": "Caja de control", "quantity": 3}


def request(method, path, data=None, key=None, token=TOKEN):
    headers = {"Authorization": "Bearer " + token}
    if data is not None:
        headers.update({"Content-Type": "application/json", "Idempotency-Key": str(key or uuid4())})
    req = Request(URL + "/api" + path, json.dumps(data).encode() if data is not None else None,
                  headers, method=method)
    try:
        response = urlopen(req, timeout=22)
    except HTTPError as error:
        response = error
    with response:
        payload = response.read()
        try:
            payload = json.loads(payload)
        except ValueError:
            payload = payload.decode(errors="replace")
        return response.status, payload, response.headers.get("X-Node-ID")


def sql_replica(query):
    psql = os.getenv("TEST_PSQL")
    command = [psql, "-h", "127.0.0.1", "-p", os.environ["TEST_REPLICA_PORT"]] if psql else [
        "docker", "compose", "exec", "-T", "replica", "psql"
    ]
    return subprocess.check_output(command + ["-XAt", "-v", "ON_ERROR_STOP=1", "-U", "postgres",
                                                "-d", "pedidos", "-c", query], text=True, timeout=8).strip()


def expect_replica(query, expected):
    started = time.monotonic()
    while time.monotonic() - started < 10:
        if sql_replica(query) == expected:
            print(f"\nRéplica observada en {(time.monotonic() - started)*1000:.1f} ms (incluye consulta)")
            return
        time.sleep(0.1)
    raise AssertionError(f"No se observó el valor esperado: {expected!r}")


class IntegrationTest(unittest.TestCase):
    def create_order(self):
        status, record, _ = request("POST", "/orders", FIELDS)
        self.assertEqual(status, 201, record)
        path = "/orders/" + record["id"]

        def cleanup():
            status, current, _ = request("GET", path)
            if status == 200:
                request("DELETE", path, {"version": current["version"]})

        self.addCleanup(cleanup)
        return path, record

    def test_auth_and_validation(self):
        self.assertEqual(request("GET", "/orders", token="")[0], 401)
        self.assertEqual(request("POST", "/orders", FIELDS, token="mala")[0], 401)
        self.assertEqual(request("POST", "/orders", FIELDS | {"quantity": -1})[0], 422)
        self.assertEqual(request("GET", "/orders?limit=1001")[0], 422)

    def test_crud_and_replication(self):
        self.assertEqual(sql_replica("SELECT pg_is_in_recovery()"), "t")
        path, record = self.create_order()
        row = " FROM orders WHERE id = '" + record["id"] + "'"
        expect_replica("SELECT status || ':' || quantity" + row, "pendiente:3")
        self.assertEqual(request("GET", path)[1], record)
        for version, status in enumerate(("en_proceso", "enviado", "entregado"), 1):
            code, updated, _ = request("PUT", path, FIELDS | {"status": status, "version": version})
            self.assertEqual((code, updated["status"], updated["version"]), (200, status, version + 1))
            expect_replica("SELECT status || ':' || version" + row, f"{status}:{version + 1}")
        key = uuid4()
        deleted = request("DELETE", path, {"version": 4}, key)
        self.assertEqual(deleted[:2], (200, {"id": record["id"], "deleted": True}))
        self.assertEqual(request("DELETE", path, {"version": 4}, key)[:2], deleted[:2])
        self.assertEqual(request("GET", path)[0], 404)
        expect_replica("SELECT count(*)" + row, "0")

    def test_concurrent_idempotency(self):
        key = uuid4()
        with ThreadPoolExecutor(6) as executor:
            results = list(executor.map(lambda _: request("POST", "/orders", FIELDS, key), range(6)))
        self.assertTrue(all(code == 201 for code, _, _ in results), results)
        record = results[0][1]
        path = "/orders/" + record["id"]
        self.addCleanup(request, "DELETE", path, {"version": 1})
        self.assertTrue(all(payload == record for _, payload, _ in results))
        self.assertEqual(request("POST", "/orders", FIELDS | {"quantity": 4}, key)[0], 409)

    def test_concurrent_versions_and_state(self):
        path, _ = self.create_order()
        forbidden = FIELDS | {"version": 1, "status": "enviado"}
        self.assertEqual(request("PUT", path, forbidden)[0], 409)
        valid = forbidden | {"status": "en_proceso"}
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda _: request("PUT", path, valid), range(2)))
        self.assertEqual(sorted(code for code, _, _ in results), [200, 409])
        self.assertEqual(request("DELETE", path, {"version": 1})[0], 409)

    def test_two_backends(self):
        nodes = {request("GET", "/live")[2] for _ in range(20)}
        self.assertEqual(nodes, {"api-a", "api-b"})


    def test_client_ownership_and_operations_access(self):
        alba, bruno = CLIENTS["demo-alba"], CLIENTS["demo-bruno"]
        self.assertEqual(request("GET", "/session", token=alba)[1]["role"], "cliente")
        key = uuid4()
        status, order, _ = request("POST", "/orders", FIELDS, key, token=alba)
        self.assertEqual(status, 201, order)
        path = "/orders/" + order["id"]
        self.addCleanup(request, "DELETE", path, {"version": 1})
        self.assertEqual(request("GET", path, token=alba)[1], order)
        self.assertEqual(request("GET", path)[1], order)
        self.assertEqual(request("GET", path, token=bruno)[0], 404)
        self.assertNotIn(order["id"], {row["id"] for row in request("GET", "/orders", token=bruno)[1]})
        self.assertEqual(request("PUT", path, FIELDS | {"status": "en_proceso", "version": 1}, token=alba)[0], 403)
        self.assertEqual(request("DELETE", path, {"version": 1}, token=bruno)[0], 403)
        self.assertEqual(request("POST", "/orders", FIELDS, key, token=bruno)[0], 409)
        self.assertEqual(request("GET", "/ops/summary", token=alba)[0], 403)
        self.assertEqual(request("GET", "/ops/summary", token="")[0], 401)
        code, summary, _ = request("GET", "/ops/summary")
        self.assertEqual(code, 200, summary)
        self.assertTrue(summary["audit_available"])
        self.assertIn("cliente", {event["actor_role"] for event in summary["orders"]})
        self.assertNotIn(FIELDS["customer"], json.dumps(summary, ensure_ascii=False))
        self.assertNotIn(order["id"], json.dumps(summary))

    def test_encrypted_storage_and_idempotency_on_replica(self):
        key = uuid4()
        status, record, _ = request("POST", "/orders", FIELDS, key)
        self.assertEqual(status, 201, record)
        path = "/orders/" + record["id"]
        self.addCleanup(request, "DELETE", path, {"version": 1})
        expect_replica("SELECT (customer IS NULL AND item IS NULL AND private_payload LIKE 'v1.%')"
                       " FROM orders WHERE id = '" + record["id"] + "'", "t")
        expect_replica("SELECT (response ? 'sealed' AND NOT (response ? 'customer') AND fingerprint LIKE 'v1.%')"
                       " FROM request_log WHERE key = '" + str(key) + "'", "t")
        self.assertEqual(request("POST", "/orders", FIELDS, key)[1], record)
