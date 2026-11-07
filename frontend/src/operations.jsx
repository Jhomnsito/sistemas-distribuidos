import React, { useEffect, useRef, useState } from "react";
import vayxerMark from "./vayxer.svg?no-inline";
import ThemeToggle from "./theme.jsx";

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

const accessActions = {
  intento_fallido: "Contraseña incorrecta",
  bloqueo_temporal: "Bloqueo temporal de 5 s",
  inicio_sesion: "Inicio de sesión",
  cierre_sesion: "Cierre de sesión",
  sesion_expirada: "Sesión expirada",
  cuenta_configurada: "Cuenta configurada",
  cuenta_bloqueada: "Cuenta bloqueada",
  cuenta_desbloqueada: "Cuenta desbloqueada",
};

function AccountConfirmation({ account, close, apply }) {
  const dialog = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current.showModal();
  }, []);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await apply(account);
      close();
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      aria-labelledby="account-title"
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else close();
      }}
    >
      <form onSubmit={submit}>
        <h2 id="account-title">
          {account.disabled ? "Desbloquear cuenta" : "Bloquear cuenta"}
        </h2>
        <p>
          <strong>{account.username}</strong>
        </p>
        <p>
          {account.disabled
            ? "Podrá iniciar sesión de nuevo. Las sesiones anteriores seguirán cerradas."
            : "Se cerrarán sus sesiones y se impedirá un nuevo acceso hasta desbloquearla."}
        </p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={close}
          >
            Cancelar
          </button>
          <button
            className={account.disabled ? "primary" : "danger"}
            disabled={busy}
          >
            {busy ? "Guardando…" : "Confirmar"}
          </button>
        </div>
      </form>
    </dialog>
  );
}

export default function Operations() {
  const [data, setData] = useState(null);
  const [account, setAccount] = useState(null);
  const [error, setError] = useState("");

  async function read(signal) {
    const response = await fetch("/api/ops/summary", {
      signal,
    });
    if (response.status === 403)
      throw new Error("Esta cuenta no tiene acceso a Operaciones.");
    if (response.status === 401) {
      window.location.replace("/");
      throw new Error("Inicia sesión para continuar.");
    }
    if (!response.ok) throw new Error("No se pudo consultar Operaciones.");
    return response.json();
  }

  async function logout() {
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("No se pudo cerrar la sesión.");
      window.location.assign("/");
    } catch (failure) {
      setError(failure.message);
    }
  }

  async function changeAccount(selected) {
    const response = await fetch(
      "/api/auth/accounts/" + encodeURIComponent(selected.username),
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blocked: !selected.disabled }),
        signal: AbortSignal.timeout(9000),
      },
    );
    if (!response.ok) {
      const failure = await response.json().catch(() => null);
      throw new Error(failure?.detail || "No se pudo cambiar la cuenta.");
    }
    setData(await read(AbortSignal.timeout(9000)));
  }

  useEffect(() => {
    const lifetime = new AbortController();
    let timer;
    async function poll() {
      try {
        const signal = AbortSignal.any([
          lifetime.signal,
          AbortSignal.timeout(9000),
        ]);
        const next = await read(signal);
        setData(next);
        setError("");
      } catch (failure) {
        if (!lifetime.signal.aborted) setError(failure.message);
      } finally {
        if (!lifetime.signal.aborted) timer = setTimeout(poll, 5000);
      }
    }
    poll();
    return () => {
      lifetime.abort();
      clearTimeout(timer);
    };
  }, []);

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
          <div className="header-actions">
            <ThemeToggle />
            <a className="signout" href="/">
              Volver a pedidos
            </a>
          </div>
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
              <button className="secondary" onClick={logout}>
                Cerrar sesión
              </button>
            )}
          </section>
        )}
        {!data ? (
          <section className="panel login">
            <h1>Operaciones</h1>
            {error ? (
              <p className="error" role="alert">
                {error}
              </p>
            ) : (
              <p>Comprobando sesión…</p>
            )}
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
                <h2>Actividad de acceso</h2>
                {data.access.events.length ? (
                  <ul>
                    {data.access.events.map((event) => (
                      <li key={event.id}>
                        <strong>
                          {accessActions[event.action] || event.action}
                        </strong>
                        <span>
                          {event.username} · {event.actor}
                        </span>
                        <time>{when(event.happened_at * 1000)}</time>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Aún no hay actividad de acceso registrada.</p>
                )}
              </section>
              <section className="panel ops-card">
                <h2>Cuentas cliente</h2>
                {data.access.clients.length ? (
                  <ul>
                    {data.access.clients.map((client) => (
                      <li key={client.username}>
                        <strong>{client.username}</strong>
                        <span>
                          {client.disabled
                            ? "Cuenta bloqueada"
                            : "Cuenta habilitada"}
                        </span>
                        <button
                          className="secondary"
                          type="button"
                          onClick={() => setAccount(client)}
                          aria-label={
                            (client.disabled ? "Desbloquear " : "Bloquear ") +
                            client.username
                          }
                        >
                          {client.disabled ? "Desbloquear" : "Bloquear"}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No hay cuentas cliente configuradas.</p>
                )}
              </section>
            </div>
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
      {account && (
        <AccountConfirmation
          account={account}
          close={() => setAccount(null)}
          apply={changeAccount}
        />
      )}
    </>
  );
}
