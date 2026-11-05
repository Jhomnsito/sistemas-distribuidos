# Informe de pruebas · Vayxer

**Fecha de ejecución** 5 de noviembre de 2026, hora de Bogotá.

## Entorno y método

Windows con Python 3.12, FastAPI 0.162.0, Uvicorn 0.54.0, Psycopg 3.3.8, NGINX 1.28.2 y PostgreSQL 16.13. NGINX sirvió el build de React y conservó la política de reintentos del proyecto, con destinos loopback fijos en el ensayo. Las dos instancias PostgreSQL y las dos APIs se ejecutaron como procesos independientes en el mismo host.

Compose 2.40.3 validó los manifiestos base y de recuperación y confirmó el volumen independiente de reemplazo. El host carecía de un motor Docker y de WSL. Quedan pendientes el arranque en contenedores, el DNS interno y la ejecución de los scripts de inicialización dentro de la imagen.

## Pruebas automatizadas

| Prueba | Verificación | Resultado |
|---|---|---|
| U1 · Matriz de estados | Los cuatro estados frente a los cuatro destinos | Pasó |
| U2 · Normalización | Recorte de espacios y conservación de acentos | Pasó |
| U3 · Campos inválidos | Vacíos, controles, booleanos, tipos y límites | Pasó |
| U4 · Huella de reintento | Cambia con el método, el recurso o el cuerpo | Pasó |
| I1 · Autorización y datos | 401 para claves inválidas y 422 para entrada o paginación inválidas | Pasó |
| I2 · CRUD y réplica | Alta, tres avances, repetición del borrado, 404 y ausencia en la réplica | Pasó |
| I3 · Idempotencia concurrente | Seis POST concurrentes devuelven el mismo registro; otro cuerpo con la clave obtiene 409 | Pasó |
| I4 · Ediciones concurrentes | Dos ediciones con la misma versión obtienen 200 y 409; se rechaza el salto de estado | Pasó |
| I5 · Dos nodos | Las sondas a través de NGINX observan ambos identificadores | Pasó |

Pasaron **4 de 4 unitarias y 5 de 5 integraciones**. La suite de integración tardó **3,991 s**. Las cinco comprobaciones en la réplica después de cada respuesta HTTP tardaron **203, 109, 109, 172 y 203 ms**, respectivamente. Los tiempos incluyen la ejecución de psql y el sondeo.

## Caída de un backend

Se enviaron sondas secuenciales autenticadas a GET /api/orders?limit=1, con 100 ms de pausa después de cada respuesta y ventanas de aproximadamente 5 s. El primer API se terminó unos 600 ms después de iniciar la ventana de inyección. Se usó el percentil por rango más próximo. Cualquier resultado distinto de HTTP 200 se cuenta como error.

| Fase | Sondas | p95 | Errores | Nodo final |
|---|---:|---:|---:|---|
| Base | 24 | 155,6 ms | 0/24 | 12 de cada nodo |
| Inyección | 17 | 1.082,3 ms | 0/17 | 1 de api-a y 16 de api-b |
| Nodo detenido | 19 | 1.141,8 ms | 0/19 | 19 de api-b |

El primer éxito observado de api-b después de confirmar la detención de api-a llegó a los **1,172 s**. Con api-a detenido, la aplicación completó un alta, una consulta, una edición y un borrado. El ensayo registró **0 errores en 60 sondas** con esta carga. El p95 durante el fallo muestra el costo de los reintentos en el laboratorio. El README explica cómo repetir el escenario con tests/fault.py y Compose.

## Recuperación de base de datos

Se creó un pedido marcador y se verificó en la réplica. Se detuvo el primario con pg_ctl, se comprobó HTTP 503 en /api/ready, se promovió la réplica y se redirigieron ambas APIs. El marcador pudo leerse y modificarse. Transcurrieron **9,413 s** desde la orden de parada hasta que la API confirmó la escritura. El ensayo automatizó las acciones del operador, así que el tiempo manual puede ser mayor.

Desde el nodo promovido se tomó una nueva copia con pg_basebackup y checkpoint rápido. Se verificaron el modo de recuperación, el estado streaming y la llegada de una nueva escritura. Transcurrieron **15,157 s** desde el inicio de la copia hasta observar esa escritura en la nueva réplica. Se usaron directorios de datos independientes.

La replicación es asíncrona. El marcador ya estaba replicado cuando se inyectó el fallo. El RPO real depende del WAL pendiente en el momento de la caída.

## Navegador

En Microsoft Edge se verificaron el rechazo de una clave inválida, el acceso, el alta, el cambio de estado, la confirmación y ejecución del borrado, la búsqueda y un ancho de 390 px sin desbordamiento del documento. Las cinco capturas del paquete local se tomaron del sistema en ejecución con datos de demostración. Vite compiló el panel y npm audit informó cero alertas para las dependencias consultadas.

## Conclusiones

La API siguió atendiendo el CRUD con un solo proceso y el proxy absorbió los fallos de conexión observados. La réplica reprodujo todas las etapas del CRUD, y el control de versiones evitó una actualización concurrente perdida. La promoción manual restauró la escritura en el ensayo. El laboratorio comparte un host y mantiene un único gateway.

Consulta el [registro de ejecución](evidencia.txt) y el [Manual técnico](manual-tecnico.md).

## Revalidación de Vayxer

La revisión posterior mantuvo la topología nativa e incorporó el monitor como proceso aparte. Pasaron **7 pruebas unitarias** (4 de dominio y 3 de cifrado) y **7 de integración** en **6,561 s**. Las nuevas integraciones comprobaron propiedad, separación administrativa y cifrado consultando la réplica. La migración cifró **7 pedidos y 44 respuestas de idempotencia** preexistentes. Se verificó mediante SQL que no quedaran nombres o productos activos en columnas en claro ni respuestas sin sellar.

| Ensayo de Vayxer | Resultado medido |
|---|---|
| Sondas base | 20, p95 251,0 ms, 0 errores |
| API A detenida | 18, p95 1.160,4 ms, 0 errores, todas por API B |
| Primera respuesta tras confirmar la detención | 1,090 s |
| Incidente visible y consultable en el monitor | Comprobado a los 6,459 s después de confirmar la parada |
| Historial persistente | Conservado al reiniciar el monitor con PostgreSQL detenido; auditoría de pedidos marcada como inaccesible |
| Navegador | SVG compartido, foco visible, CRUD de administración, acceso de cliente, rechazo de cliente en Operaciones y vista a 390 px sin desplazamiento lateral |

Los tiempos anteriores a esta sección corresponden al primer ensayo nativo. La recuperación de PostgreSQL de ese ensayo verificó promoción y reemplazo. La revalidación de Vayxer comprobó la pérdida del primario y la conservación del historial del monitor. Los manifiestos base, de recuperación y TLS pasaron la validación de configuración.
