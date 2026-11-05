"""Comprueba detección, recuperación e historial tras reiniciar el observador."""
import subprocess
import time

from test_integration import request


def summary():
    status, body, _ = request("GET", "/ops/summary")
    return body if status == 200 else {}


def wait_for(predicate, seconds=35):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = predicate(summary())
        if value:
            return value
        time.sleep(0.5)
    raise AssertionError("No se observó el cambio de estado esperado")


def state(data, expected):
    return any(item["service"] == "api-a" and item["state"] == expected
               for item in data.get("services", []))


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True, timeout=60)


def main():
    wait_for(lambda data: state(data, "operativo"))
    started = time.monotonic()
    try:
        compose("stop", "-t", "1", "api-a")
        stopped = time.monotonic()
        wait_for(lambda data: state(data, "caido"))
        print(f"Caída visible {time.monotonic() - stopped:.3f} s tras confirmar la parada.")
        code, _, node = request("GET", "/orders?limit=1")
        assert (code, node) == (200, "api-b")
        event_id = wait_for(lambda data: next(
            (item["id"] for item in data.get("events", []) if item["service"] == "api-a" and item["state"] == "caido"),
            None,
        ))
        compose("restart", "monitor")
        wait_for(lambda data: any(item["id"] == event_id for item in data.get("events", [])))
        print("Evento conservado al reiniciar el monitor.")
    finally:
        compose("start", "api-a")
    wait_for(lambda data: state(data, "operativo"))
    print(f"Recuperación observada a los {time.monotonic()-started:.3f} s desde el inicio del ensayo.")


if __name__ == "__main__":
    main()
