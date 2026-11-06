import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import Operations from "./operations.jsx";
import BrandArtwork from "./BrandArtwork.jsx";
import vayxerMark from "./vayxer.svg?no-inline";

const states = [
  ["pendiente", "Pendiente", "clock"],
  ["en_proceso", "En proceso", "cycle"],
  ["enviado", "Enviado", "truck"],
  ["entregado", "Entregado", "check"],
];
const glyphs = {
  box: "M12 3 3 8v8l9 5 9-5V8l-9-5Zm0 18v-8m-9-5 9 5 9-5M7.5 5.5l9 5",
  clock: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM12 6v6l4 2",
  cycle: "M20 7A9 9 0 0 0 5 5L2 8m0-5v5h5m-3 9a9 9 0 0 0 15 2l3-3m0 5v-5h-5",
  truck:
    "M1 4h14v13H1V4Zm14 5h4l4 4v4h-8m-7 0a2 2 0 1 1-4 0m16 0a2 2 0 1 1-4 0",
  check: "M5 12l4 4L19 6",
  plus: "M12 5v14M5 12h14",
  search: "M20 20l-4.5-4.5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z",
  edit: "m4 16-1 5 5-1L20 8l-4-4L4 16Zm9-9 4 4",
  trash: "M3 6h18M8 6V3h8v3M5 6l1 15h12l1-15M10 10v7m4-7v7",
  arrow: "M5 12h14m-6-6 6 6-6 6",
};
const pageSize = 12;
const empty = { customer: "", item: "", quantity: 1 };
const formatDate = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "short",
});

function Icon({ name, size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={glyphs[name]} />
    </svg>
  );
}

async function api(path, token, method = "GET", body, key) {
  const headers = { Authorization: "Bearer " + token };
  if (body) {
    headers["Content-Type"] = "application/json";
    headers["Idempotency-Key"] = key;
  }
  const response = await fetch(
    path.startsWith("/api/") ? path : "/api/orders" + path,
    {
      method,
      headers,
      body: body && JSON.stringify(body),
      signal: AbortSignal.timeout(22000),
    },
  );
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw Object.assign(
      new Error(data?.detail || "El servicio no respondió correctamente."),
      { status: response.status },
    );
  }
  return { data, node: response.headers.get("X-Node-ID") };
}

function OrderDialog({ record, remove, save, close }) {
  const dialog = useRef(null);
  const [fields, setFields] = useState(record || empty);
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current.showModal();
  }, []);
  const currentIndex = states.findIndex(([value]) => value === record?.status);
  const title = remove
    ? "Eliminar pedido"
    : record
      ? "Editar pedido"
      : "Nuevo pedido";

  async function submit(event) {
    event.preventDefault();
    const body = remove
      ? { version: record.version }
      : {
          customer: fields.customer.trim(),
          item: fields.item.trim(),
          quantity: Number(fields.quantity),
          ...(record && { version: record.version, status: fields.status }),
        };
    const attempt = pending || { body, key: crypto.randomUUID() };
    setPending(attempt);
    setBusy(true);
    setError("");
    try {
      await save(record, remove, attempt);
    } catch (failure) {
      const uncertain = !failure.status || failure.status >= 500;
      if (!uncertain) setPending(null);
      setError(
        uncertain
          ? "No se pudo confirmar el resultado. Reintenta para consultar la misma operación."
          : failure.message,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy && !pending) close();
      }}
    >
      <form onSubmit={submit}>
        <p className="eyebrow">GESTIÓN DE PEDIDOS</p>
        <h2 id="dialog-title">{title}</h2>
        {remove ? (
          <p>
            Se eliminará el pedido de <strong>{record.customer}</strong> para{" "}
            <strong>{record.item}</strong>. Confirma para continuar.
          </p>
        ) : (
          <fieldset disabled={busy || Boolean(pending)}>
            <label>
              Cliente
              <input
                autoFocus
                required
                maxLength={100}
                value={fields.customer}
                onChange={(event) =>
                  setFields({ ...fields, customer: event.target.value })
                }
              />
            </label>
            <label>
              Producto
              <input
                required
                maxLength={160}
                value={fields.item}
                onChange={(event) =>
                  setFields({ ...fields, item: event.target.value })
                }
              />
            </label>
            <label>
              Unidades
              <input
                required
                type="number"
                min="1"
                max="999"
                value={fields.quantity}
                onChange={(event) =>
                  setFields({ ...fields, quantity: event.target.value })
                }
              />
            </label>
            {record && (
              <label>
                Estado
                <select
                  value={fields.status}
                  onChange={(event) =>
                    setFields({ ...fields, status: event.target.value })
                  }
                >
                  {states
                    .slice(currentIndex, currentIndex + 2)
                    .map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                </select>
              </label>
            )}
          </fieldset>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={close}
          >
            {pending ? "Cerrar y actualizar" : "Cancelar"}
          </button>
          <button disabled={busy} className={remove ? "danger" : "primary"}>
            {busy
              ? "Guardando…"
              : pending
                ? "Reintentar"
                : remove
                  ? "Eliminar pedido"
                  : "Guardar pedido"}
          </button>
        </div>
      </form>
    </dialog>
  );
}

function App() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [entry, setEntry] = useState("");
  const [orders, setOrders] = useState([]);
  const [node, setNode] = useState(null);
  const [page, setPage] = useState(0);
  const [more, setMore] = useState(false);
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState(null);

  async function refresh(activeToken = token, activePage = page) {
    setBusy(true);
    setError("");
    try {
      const session = token ? null : await api("/api/session", activeToken);
      const result = await api(
        "?limit=" + (pageSize + 1) + "&offset=" + activePage * pageSize,
        activeToken,
      );
      if (activePage > 0 && !result.data.length)
        return await refresh(activeToken, activePage - 1);
      setOrders(result.data.slice(0, pageSize));
      setMore(result.data.length > pageSize);
      setNode(result.node);
      setPage(activePage);
      setToken(activeToken);
      if (session) setRole(session.data.role);
      setEntry("");
    } catch (failure) {
      setNode(null);
      setError(failure.message || "No se pudo consultar el servicio.");
      if (failure.status === 401) {
        setToken("");
        setOrders([]);
      }
    } finally {
      setBusy(false);
    }
  }

  async function save(record, remove, { body, key }) {
    await api(
      record ? "/" + record.id : "",
      token,
      remove ? "DELETE" : record ? "PUT" : "POST",
      body,
      key,
    );
    setDialog(null);
    setNotice(
      remove
        ? "Pedido eliminado."
        : record
          ? "Pedido actualizado."
          : "Pedido registrado.",
    );
    await refresh(token, record ? page : 0);
  }

  const term = search.trim().toLocaleLowerCase("es");
  const visible = orders.filter(
    (order) =>
      (!state || order.status === state) &&
      [order.id, order.customer, order.item].some((value) =>
        value.toLocaleLowerCase("es").includes(term),
      ),
  );

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
              Vayxer<small>GESTIÓN LOGÍSTICA</small>
            </div>
          </div>
          {token && (
            <div className="header-actions">
              {role === "admin" && (
                <a className="signout" href="/operaciones">
                  Operaciones
                </a>
              )}
              <span className="node">
                <i className={node ? "online" : ""} />
                {node ? "Última respuesta · " + node : "Sin confirmación"}
              </span>
              <button
                className="signout"
                disabled={busy}
                onClick={() => {
                  setToken("");
                  setOrders([]);
                  setNode(null);
                  setPage(0);
                  setError("");
                  setSearch("");
                  setState("");
                  setNotice("");
                }}
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </header>
      <main className={token ? "shell" : "shell access-layout"}>
        <section className="hero">
          <div>
            <p className="eyebrow">CENTRO DE OPERACIONES</p>
            <h1>Control de pedidos</h1>
            <p>Registra envíos y acompaña cada pedido hasta su entrega.</p>
          </div>
          {!token && <BrandArtwork />}
          {token && (
            <button className="primary" onClick={() => setDialog({})}>
              <Icon name="plus" /> Nuevo pedido
            </button>
          )}
        </section>
        {!token ? (
          <section className="panel login">
            <h2>Acceso al panel</h2>
            <p>Ingresa tu clave de cliente o administrador.</p>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                refresh(entry.trim(), 0);
              }}
            >
              <label>
                Clave de acceso
                <input
                  type="password"
                  autoComplete="off"
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
                {busy ? "Verificando…" : "Entrar al panel"}{" "}
                <Icon name="arrow" />
              </button>
            </form>
          </section>
        ) : (
          <>
            <p className="eyebrow section-label">ESTADOS EN ESTA PÁGINA</p>
            <section className="metrics" aria-label="Estados en esta página">
              {states.map(([value, label, icon]) => (
                <button
                  key={value}
                  className="metric panel"
                  aria-pressed={state === value}
                  onClick={() => setState(state === value ? "" : value)}
                >
                  <span className={"metric-icon " + value}>
                    <Icon name={icon} />
                  </span>
                  <span>
                    <span className="metric-label">{label}</span>
                    <strong>
                      {orders.filter((order) => order.status === value).length}
                    </strong>
                  </span>
                </button>
              ))}
            </section>
            <section
              className="panel registry"
              aria-labelledby="registry-title"
            >
              <div className="registry-heading">
                <div>
                  <h2 id="registry-title">Registro de pedidos</h2>
                  <p>Consulta y actualiza los pedidos de esta página.</p>
                </div>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => refresh()}
                >
                  <Icon name="cycle" size={16} /> Actualizar
                </button>
              </div>
              <div className="filters">
                <label>
                  <Icon name="search" size={17} />
                  <input
                    type="search"
                    aria-label="Buscar en esta página"
                    placeholder="Buscar cliente, producto o ID"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                <select
                  aria-label="Filtrar por estado"
                  value={state}
                  onChange={(event) => setState(event.target.value)}
                >
                  <option value="">Todos los estados</option>
                  {states.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="feedback" aria-live="polite">
                {busy ? "Cargando pedidos…" : notice}
              </div>
              {error && (
                <p role="alert" className="error">
                  {error} Los datos visibles corresponden a la última consulta
                  exitosa.
                </p>
              )}
              {visible.length ? (
                <div className="table-wrap">
                  <table role="table">
                    <thead role="rowgroup">
                      <tr role="row">
                        <th role="columnheader" scope="col">
                          Pedido / cliente
                        </th>
                        <th role="columnheader" scope="col">
                          Producto
                        </th>
                        <th role="columnheader" scope="col">
                          Unidades
                        </th>
                        <th role="columnheader" scope="col">
                          Estado
                        </th>
                        <th role="columnheader" scope="col">
                          Registro
                        </th>
                        {role === "admin" && (
                          <th role="columnheader" scope="col">
                            Acciones
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody role="rowgroup">
                      {visible.map((order) => (
                        <tr role="row" key={order.id}>
                          <td role="cell">
                            <strong>{order.customer}</strong>
                            <small title={order.id}>
                              #{order.id.slice(0, 8).toUpperCase()}
                            </small>
                          </td>
                          <td role="cell">{order.item}</td>
                          <td role="cell">
                            {order.quantity}
                            <span className="mobile-units" aria-hidden="true">
                              {" "}
                              uds.
                            </span>
                          </td>
                          <td role="cell">
                            <span className={"badge " + order.status}>
                              {
                                states.find(
                                  ([value]) => value === order.status,
                                )[1]
                              }
                            </span>
                          </td>
                          <td role="cell">
                            <time dateTime={order.created_at}>
                              {formatDate.format(new Date(order.created_at))}
                            </time>
                          </td>
                          {role === "admin" && (
                            <td role="cell">
                              <div className="row-actions">
                                <button
                                  aria-label={
                                    "Editar pedido de " + order.customer
                                  }
                                  onClick={() => setDialog({ record: order })}
                                >
                                  <Icon name="edit" size={17} />
                                </button>
                                <button
                                  aria-label={
                                    "Eliminar pedido de " + order.customer
                                  }
                                  onClick={() =>
                                    setDialog({ record: order, remove: true })
                                  }
                                >
                                  <Icon name="trash" size={17} />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                !busy && (
                  <div className="empty">
                    <Icon name="box" size={30} />
                    <strong>
                      {orders.length
                        ? "Sin coincidencias"
                        : "Sin pedidos para mostrar"}
                    </strong>
                    <p>
                      {orders.length
                        ? "Ajusta la búsqueda o el filtro."
                        : "Los pedidos registrados aparecerán aquí."}
                    </p>
                  </div>
                )
              )}
              <div className="pagination">
                <span>
                  Página {page + 1} · {visible.length} visibles
                </span>
                <div>
                  <button
                    className="secondary"
                    disabled={busy || !page}
                    onClick={() => refresh(token, page - 1)}
                  >
                    Anterior
                  </button>
                  <button
                    className="secondary"
                    disabled={busy || !more}
                    onClick={() => refresh(token, page + 1)}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </section>
          </>
        )}
        <footer>
          Vayxer <span>·</span> Sistema distribuido de pedidos
        </footer>
      </main>
      {dialog && (
        <OrderDialog
          {...dialog}
          save={save}
          close={() => {
            setDialog(null);
            refresh();
          }}
        />
      )}
    </>
  );
}

const operations = window.location.pathname === "/operaciones";
if (operations) document.title = "Vayxer · Operaciones";
createRoot(document.getElementById("root")).render(
  operations ? <Operations /> : <App />,
);
