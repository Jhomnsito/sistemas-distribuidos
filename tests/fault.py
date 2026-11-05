"""Mide sondas GET y verifica una escritura con un nodo detenido."""
import argparse
import math
import shlex
import subprocess
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from test_integration import FIELDS, request


def sample(seconds, started=None):
    started = started if started is not None else time.perf_counter()
    samples = []
    while time.perf_counter() - started < seconds:
        sent = time.perf_counter()
        try:
            status, _, node = request("GET", "/orders?limit=1")
        except OSError:
            status, node = 0, None
        completed = time.perf_counter()
        samples.append((sent - started, completed - started, status, node))
        time.sleep(0.10)

    return samples


def summarize(name, samples):
    delays = sorted((end - start) * 1000 for start, end, *_ in samples)
    failures = sum(code != 200 for _, _, code, _ in samples)
    nodes = Counter(node for _, _, _, node in samples if node)
    print(f"{name}: n={len(delays)} p95={delays[math.ceil(.95*len(delays))-1]:.1f} ms "
          f"errores={failures}/{len(delays)} ({100*failures/len(delays):.2f}%) nodos={dict(nodes)}")


def stop_backend(command, started):
    subprocess.run(shlex.split(command), check=True, timeout=30)
    return time.perf_counter() - started


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", default="docker compose stop -t 1 api-a")
    parser.add_argument("--start", default="docker compose start api-a")
    parser.add_argument("--seconds", type=int, default=5)
    args = parser.parse_args()
    summarize("Base", sample(args.seconds))
    try:
        started = time.perf_counter()
        with ThreadPoolExecutor(1) as executor:
            stopped = executor.submit(stop_backend, args.stop, started)
            samples = sample(args.seconds, started)
            stopped_at = stopped.result()
        summarize("Durante la inyección", samples)
        degraded_started = time.perf_counter()
        degraded = sample(args.seconds, degraded_started)
        degraded_offset = degraded_started - started
        confirmed = samples + [(start + degraded_offset, end + degraded_offset, code, node)
                               for start, end, code, node in degraded]
        first_success = next((end for _, end, code, node in confirmed
                              if end >= stopped_at and code == 200 and node == "api-b"), None)
        assert first_success is not None, "No hubo respuesta sana tras detener api-a"
        print(f"Primer éxito observado tras confirmar la detención: {first_success - stopped_at:.3f} s")
        summarize("Nodo detenido", degraded)
        assert all(code == 200 and node == "api-b" for _, _, code, node in degraded)
        code, record, node = request("POST", "/orders", FIELDS)
        assert (code, node) == (201, "api-b"), (code, record, node)
        path = "/orders/" + record["id"]
        assert request("GET", path)[1] == record
        assert request("PUT", path, FIELDS | {"status": "en_proceso", "version": 1})[0] == 200
        assert request("DELETE", path, {"version": 2})[0] == 200
        print("CRUD comprobado durante la caída de api-a.")
    finally:
        subprocess.run(shlex.split(args.start), check=True)


if __name__ == "__main__":
    main()
