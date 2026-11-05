# Manual técnico · Vayxer

## Arquitectura

```mermaid
flowchart LR
  U["Navegador · React"] -->|"HTTP en loopback"| G["NGINX · estáticos y proxy"]
  G -->|"REST"| A["FastAPI · api-a"]
  G -->|"REST"| B["FastAPI · api-b"]
  A -->|"SQL · lectura y escritura"| P["PostgreSQL primario"]
  B -->|"SQL · lectura y escritura"| P
  P -->|"WAL físico asíncrono"| S["PostgreSQL réplica"]
  G -->|"REST de operaciones"| M["Monitor · FastAPI y SQLite"]
  M -.->|"Sondas"| A
  M -.->|"Sondas"| B
  M -.->|"Salud y auditoría"| P
  M -.->|"Sonda de streaming"| S
  O["Administrador"] -.->|"Verificación y promoción manual"| S
```

En Compose, `gateway` publica un único puerto en loopback. La red `edge` conecta al proxy con ambas APIs. La red interna `data` conecta las APIs y ambas instancias PostgreSQL, sin publicar puertos. Los nodos son independientes y sin estado local. El volumen de cada base conserva su propia copia.

```mermaid
sequenceDiagram
  participant UI as Navegador
  participant G as NGINX
  participant A as FastAPI
  participant P as Primario
  participant R as Réplica
  UI->>G: POST, PUT o DELETE + token y UUID
  G->>A: Reenvío a un nodo disponible
  A->>P: INSERT clave, validación y cambio en una transacción
  P-->>A: Confirmación local de COMMIT
  A-->>UI: Resultado vía NGINX, con X-Node-ID
  P-->>R: Envío y reproducción asíncrona de WAL
```

El flujo indica que el API espera el commit local. La reproducción en la réplica puede ocurrir antes o después de la respuesta del cliente.

## API y consistencia

| Método | Ruta | Entrada y resultado |
|---|---|---|
| GET | `/api/live` | Vida del proceso, 200 |
| GET | `/api/ready` | Conexión al nodo escribible y esquema disponible, 200 o 503 |
| GET | `/api/orders` | `limit` de 1 a 100 y `offset`, por fecha de creación descendente e ID |
| GET | `/api/orders/{id}` | Consulta por UUID, 200 o 404 |
| POST | `/api/orders` | `customer`, `item`, `quantity`; 201 y estado inicial pendiente |
| PUT | `/api/orders/{id}` | Campos anteriores, `version` y `status`; 200 y versión nueva |
| DELETE | `/api/orders/{id}` | Cuerpo JSON con `version`; 200 con ID y confirmación |

Las rutas de pedidos exigen `Authorization: Bearer <APP_TOKEN>`. Los clientes crean y consultan pedidos propios. La API filtra por identidad estable, devuelve 404 ante pedidos ajenos y reserva PUT/DELETE a administración (403 para clientes). GET /api/session informa el rol autenticado. GET /api/ops/summary exige administración y devuelve sondas e historial. Todas las mutaciones requieren un UUID en `Idempotency-Key`. Una repetición exitosa con el mismo método, pedido y cuerpo normalizado devuelve el resultado original. Reutilizar la clave con otra solicitud devuelve 409. Un error de validación devuelve 422. Los fallos de transacción revierten el cambio y la reserva de clave juntos.

PostgreSQL serializa las solicitudes con una misma clave mediante la restricción única. Para edición y borrado, `FOR UPDATE` serializa cambios en una fila y `version` rechaza escrituras basadas en una copia anterior. Los estados permiten conservar el actual o avanzar un paso: pendiente → en proceso → enviado → entregado. Las lecturas salen del primario para que una consulta posterior al commit vea el cambio.

El registro de idempotencia guarda respuestas exitosas cifradas. La clave UUID queda vinculada al método, recurso, cuerpo y cuenta. La auditoría de altas, ediciones, cambios de estado y borrados se escribe en la misma transacción y se replica. Guarda hora, acción, rol y estados, sin nombres, productos, identificadores de pedidos, tokens ni cuerpos.

## Roles, claves y cifrado

`APP_TOKEN` identifica al administrador. `CLIENT_TOKENS` es un objeto JSON de identificadores estables y tokens individuales. Cada token debe ser único y tener al menos 32 caracteres ASCII. Para añadir una cuenta, genera un token con `python -c "from secrets import token_urlsafe; print(token_urlsafe(36))"`, añade el par al objeto JSON en `.env` y recrea ambas APIs y el monitor. Para revocar el acceso, elimina el par o sustituye su token. Conserva el identificador cuando rotes un token. Este laboratorio gestiona las cuentas mediante configuración y memoria del proceso.

Los campos cliente y producto y el resultado de las mutaciones se protegen con AES-256-GCM de Cryptography. Cada valor usa un nonce aleatorio de 96 bits. Los datos autenticados asociados vinculan el texto cifrado al pedido o a la solicitud y su cuenta. Las solicitudes nuevas usan una huella HMAC con una subclave separada. Los números de unidades, estados, fechas, identificadores de fila y de propietario se conservan en claro para las consultas. La clave está fuera del repositorio en `DATA_KEY` y debe conservarse junto con el plan de recuperación. Perderla impide leer los campos protegidos. El laboratorio emplea una clave para ambos nodos y no incluye rotación automática. Protege el host, el archivo `.env`, los respaldos y el acceso a Docker, que puede inspeccionar las variables de entorno. El cifrado no evita que una API comprometida con acceso a la clave lea datos.

### Migración de una instalación previa

1. Respalda el volumen y la configuración. Ejecuta `python deploy/setup.py --upgrade` para añadir las variables faltantes sin cambiar las claves existentes.
2. Detén las APIs anteriores. Ejecuta `docker compose exec -T primary psql -v ON_ERROR_STOP=1 -U postgres -d pedidos -f /opt/pedidos/02-security.sql`. Si el contenedor anterior no tiene ese archivo montado, usa `Get-Content -Raw database/02-security.sql | docker compose exec -T primary psql -v ON_ERROR_STOP=1 -U postgres -d pedidos` en PowerShell.
3. Compila la imagen y ejecuta `docker compose run --rm --no-deps api-a python encrypt_legacy.py`. El proceso cifra en lotes y puede repetirse. Después recrea las APIs, el monitor y el gateway con `docker compose up -d --build --wait`.
4. Los pedidos anteriores quedan visibles para administración. Para atribuir uno a un cliente, verifica primero la relación con evidencia externa y actualiza `owner_id` a su identificador estable en PostgreSQL. No infieras la propiedad por el nombre del comprador. Las huellas antiguas se conservan para respetar reintentos existentes. Copias previas, WAL y versiones de fila anteriores pueden conservar información histórica en claro.

### HTTPS local opcional

Con OpenSSL, crea una carpeta `local-tls` y genera un certificado de laboratorio con SAN para el nombre y la dirección usados por el navegador:

```sh
mkdir local-tls
openssl req -x509 -newkey rsa:3072 -sha256 -days 30 -nodes -keyout local-tls/key.pem -out local-tls/cert.pem -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
docker compose -f compose.yaml -f tls.compose.yaml up -d --build --wait
curl --cacert local-tls/cert.pem https://127.0.0.1:8443/api/ready
```

Confía en el certificado de laboratorio en el cliente o usa un certificado emitido por una CA de confianza. El override requiere Compose 2.24.4 o posterior y publica solo HTTPS en loopback. TLS protege del navegador al gateway. Las redes internas de Compose usan HTTP y PostgreSQL con SCRAM, sin TLS entre servicios.

## Tolerancia y diagnóstico

NGINX distribuye solicitudes entre dos destinos y reintenta ante errores de transporte y 502/503/504. En las mutaciones, los dos destinos comparten la misma tabla de idempotencia. Dos intentos agotan el presupuesto del proxy. La API registra nodo, ruta, código y duración, y NGINX registra tiempo total y destinos consultados. Los logs excluyen credenciales, cuerpos, parámetros y UUID de pedidos. El monitor sondea por separado gateway, vida y disponibilidad de ambas APIs, primario y recepción WAL de la réplica. Persiste solo las transiciones en SQLite sobre un volumen independiente. Un proceso vivo sin acceso a la base se marca degradado. El panel muestra la hora de la última sonda y consulta cada cinco segundos. La respuesta identifica al nodo final mediante `X-Node-ID`.

La réplica se inicia con `pg_basebackup -X stream -R`. Usa rol dedicado y autenticación SCRAM, configura 256 MB como mínimo de WAL reciente a conservar mediante wal_keep_size y recibe WAL continuamente. Si la desconexión supera el WAL disponible, se requiere otra copia base. La réplica se consulta para comprobar convergencia. El esquema y los registros de idempotencia también viajan por WAL.

- **Pérdida de un API.** El otro nodo puede atender el CRUD mientras NGINX y el primario estén disponibles. Puede haber demoras de reconexión y fallos de solicitudes si se agotan los intentos.
- **Pérdida de la réplica.** El primario sigue confirmando localmente. Se pierde la copia en línea durante el incidente.
- **Pérdida del primario.** El servicio devuelve 503 o un error de gateway durante el cambio manual. Puede perderse WAL confirmado localmente que aún no llegó a la réplica. El RPO depende del atraso y puede crecer con una desconexión. Una clave de idempotencia perdida queda sujeta al mismo límite.
- **Pérdida del gateway.** Las pantallas quedan inaccesibles. Si el monitor sigue activo, registra la caída y el retorno. Inspecciona `docker compose ps gateway` y `docker compose logs gateway`, corrige la causa y reinicia o recrea el gateway. Comprueba la portada y `/api/ready`.
- **Pérdida del monitor o del host.** Un fallo del monitor no detiene el CRUD. Reinícialo y conserva su volumen para consultar eventos previos. El sistema comparte un host y la réplica física tampoco sustituye un respaldo restaurable.

Para observar replicación, usa estas consultas desde el primario y la réplica, respectivamente:

```sql
SELECT application_name, state, sync_state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS atraso_bytes
FROM pg_stat_replication;
SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

## Recuperación manual del primario en Compose

Usa un laboratorio desechable para ensayar. En una caída real, anota la hora, confirma la recuperación de WAL disponible y evalúa posible pérdida antes de aceptar nuevas escrituras. Nunca promociones mientras el primario anterior pueda aceptar escrituras.

1. Detén el primario con `docker compose stop primary`. Comprueba con `docker compose ps -a primary` que esté detenido. Si la interrupción es de red, aísla el servidor del tráfico y verifica el aislamiento por otro canal antes de avanzar. Suspende cualquier proceso que pudiera volver a iniciarlo.
2. Confirma que la réplica sigue en recuperación y revisa las posiciones recibida y reproducida. Cuando la reproducción haya alcanzado el WAL disponible, promueve:

   ```sh
   docker compose exec -T replica psql -U postgres -d pedidos -v ON_ERROR_STOP=1 -c "SELECT pg_promote(true, 60);"
   docker compose exec -T replica psql -U postgres -d pedidos -Atc "SELECT pg_is_in_recovery();"
   ```

   El primer comando debe indicar que la promoción se completó. El segundo debe devolver `f`.

3. En `.env`, cambia `DB_HOST=primary` por `DB_HOST=replica` y configura `REPLICA_HOST=replacement` y quita de la terminal cualquier variable `DB_HOST` que tenga prioridad. Recrea las APIs y el monitor.

   ```sh
   docker compose up -d --no-deps --force-recreate api-a api-b monitor
   curl http://127.0.0.1:8080/api/ready
   ```

4. Lee un pedido anterior y comprueba una mutación controlada. Anota RTO y concilia pedidos cuyo resultado era incierto con los clientes. Mantén detenido el primario anterior y conserva su volumen para diagnóstico o conciliación.
5. Incorpora una copia nueva con un volumen independiente y la réplica promovida como origen.

   ```sh
   docker compose -f compose.yaml -f recovery.compose.yaml up -d --no-deps replacement
   docker compose -f compose.yaml -f recovery.compose.yaml exec -T replacement psql -U postgres -d pedidos -c "SELECT pg_is_in_recovery(), status FROM pg_stat_wal_receiver"
   ```

   Espera `t` y `streaming`. Comprueba convergencia con otra escritura controlada. En la topología recuperada, inicia solo `gateway replica replacement api-a api-b monitor` con ambos manifiestos y `DB_HOST=replica`. Evita el arranque global del manifiesto base durante la recuperación. La copia antigua puede archivarse según el procedimiento del equipo.

## Decisiones

| Decisión | Motivo y costo |
|---|---|
| ADR-01 · Dos APIs sin estado | Aislar la caída de un proceso y permitir cambio de destino. La BD centraliza coordinación. |
| ADR-02 · WAL asíncrono y promoción manual | Permite que la réplica se ausente sin bloquear al primario. Acepta posible pérdida de escrituras y un intervalo de indisponibilidad al promover. |
| ADR-03 · Idempotencia transaccional y versión por fila | Evitar duplicados por reintentos y actualizaciones perdidas. El registro crece con cada mutación exitosa. |
| ADR-04 · REST, sondas periódicas y claves individuales | Cubrir el flujo con pocos componentes. El monitor observa salud periódicamente y las listas de pedidos se actualizan al consultar o guardar. |

Fuentes técnicas oficiales. [PostgreSQL 16 · Streaming replication y promoción](https://www.postgresql.org/docs/16/warm-standby.html) · [PostgreSQL 16 · pg_basebackup](https://www.postgresql.org/docs/16/app-pgbasebackup.html) · [NGINX · proxy_next_upstream](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream)
