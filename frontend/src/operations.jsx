import React, { useEffect, useState } from "react";
import vayxerMark from "./vayxer.svg?no-inline";

const names = {
  gateway: "Gateway",
  "api-a": "API A",
  "api-b": "API B",
  primario: "Primario activo",
  replica: "Réplica",
};
const health = {
  operativo: "Operativo",
  degradado: "Degradado",
  caido: "Caído",
};
const actions = {
  creado: "Alta",
  editado: "Edición",
  estado: "Cambio de estado",
  eliminado: "Borrado",
};
const date = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "short",
  timeStyle: "medium",
});
const when = (time) => date.format(new Date(time));
const label = (value) => value?.replaceAll("_", " ") || "—";

export default function Operations() {
  const [token, setToken] = useState("");
  const [entry, setEntry] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function read(key, signal = AbortSignal.timeout(9000)) {
    const response = await fetch("/api/ops/summary", {
      headers: { Authorization: "Bearer " + key },
      signal,
    });
    if (response.status === 403)
      throw new Error("Esta cuenta no tiene acceso a Operaciones.");
    if (response.status === 401)
      throw new Error("Clave administrativa incorrecta o ausente.");
    if (!response.ok) throw new Error("No se pudo consultar Operaciones.");
    return response.json();
  }

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const key = entry.trim();
      setData(await read(key));
      setEntry("");
      setToken(key);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!token) return;
    const lifetime = new AbortController();
    let timer;
    async function poll() {
      try {
        const signal = AbortSignal.any([
          lifetime.signal,
          AbortSignal.timeout(9000),
        ]);
        const next = await read(token, signal);
        setData(next);
        setError("");
      } catch {
        if (!lifetime.signal.aborted)
          setError(
            "No se pudo actualizar. Se muestra el último estado conocido.",
          );
      } finally {
        if (!lifetime.signal.aborted) timer = setTimeout(poll, 5000);
      }
    }
    timer = setTimeout(poll, 5000);
    return () => {
      lifetime.abort();
      clearTimeout(timer);
    };
  }, [token]);

  return (
    <>
      <header className="top">
        <div className="shell bar">
          <div className="brand">
            <img
              className="brand-mark"
              src={vayxerMark}
              alt=""
              width="42"
              height="42"
            />
            <div>
              Vayxer<small>OPERACIONES</small>
            </div>
          </div>
          <a className="signout" href="/">
            Volver a pedidos
          </a>
        </div>
      </header>
      <main className={data ? "shell" : "shell access-layout"}>
        {data && (
          <section className="hero">
            <div>
              <p className="eyebrow">ADMINISTRACIÓN</p>
              <h1>Operaciones</h1>
              <p>
                Consulta la salud de los servicios y los eventos del sistema.
              </p>
            </div>
            {data && (
              <button
                className="secondary"
                onClick={() => {
                  setToken("");
                  setData(null);
                  setError("");
                }}
              >
                Cerrar sesión
              </button>
            )}
          </section>
        )}
        {!data ? (
          <section className="panel login">
            <h1>Acceso administrativo</h1>
            <p>Usa la clave de administrador.</p>
            <form onSubmit={login}>
              <label>
                Clave administrativa
                <input
                  type="password"
                  required
                  value={entry}
                  onChange={(event) => setEntry(event.target.value)}
                />
              </label>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <button className="primary" disabled={busy}>
                {busy ? "Verificando…" : "Entrar a Operaciones"}
              </button>
            </form>
          </section>
        ) : (
          <>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <section className="ops-metrics" aria-label="Salud de servicios">
              {Object.entries(names).map(([service, name]) => {
                const current = data.services.find(
                  (item) => item.service === service,
                );
                return (
                  <article className="panel ops-card" key={service}>
                    <h2>{name}</h2>
                    <span
                      className={"badge " + (current?.state || "pendiente")}
                    >
                      {health[current?.state] || "Sin medición"}
                    </span>
                    <small>
                      {current
                        ? when(current.checked_at)
                        : "Esperando primera sonda"}
                    </small>
                  </article>
                );
              })}
            </section>
            <div className="ops-history">
              <section className="panel ops-card">
                <h2>Historial de salud</h2>
                {data.events.length ? (
                  <ul>
                    {data.events.map((event) => (
                      <li key={event.id}>
                        <strong>{names[event.service]}</strong>
                        <span>
                          {event.previous ? health[event.previous] + " → " : ""}
                          {health[event.state]}
                        </span>
                        <time>{when(event.happened_at)}</time>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Aún no hay cambios registrados.</p>
                )}
              </section>
              <section className="panel ops-card">
                <h2>Actividad de pedidos</h2>
                {!data.audit_available ? (
                  <p role="status">
                    Auditoría temporalmente inaccesible. El historial de salud
                    sigue disponible.
                  </p>
                ) : data.orders.length ? (
                  <ul>
                    {data.orders.map((event, index) => (
                      <li key={index}>
                        <strong>{actions[event.action]}</strong>
                        <span>
                          {label(event.from_status)} → {label(event.to_status)}{" "}
                          · {event.actor_role}
                        </span>
                        <time>{when(event.happened_at)}</time>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Aún no hay actividad registrada.</p>
                )}
              </section>
            </div>
          </>
        )}
      </main>
    </>
  );
}
