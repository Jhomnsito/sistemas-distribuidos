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

En Microsoft Edge se verificaron el rechazo de una clave inválida, el acceso, el alta, el cambio de estado, la confirmación y ejecución del borrado, la búsqueda y un ancho de 390 px sin desbordamiento del documento. Las cinco capturas del manual se tomaron del sistema en ejecución con datos de demostración. Vite compiló el panel y npm audit informó cero alertas para las dependencias consultadas.

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

## Verificación en Docker Desktop · 6 de noviembre de 2026

Se desplegó el commit 79704b4 desde GitHub con Docker Engine 29.9.2, Compose 5.6.1 y PostgreSQL 16.15. El gateway, ambos nodos, el monitor, el primario y la réplica iniciaron en el proyecto local. El primer despliegue detectó una carrera de arranque de la réplica. Se añadió una espera activa por el primario y una copia inicial con checkpoint rápido. Un proyecto separado arrancó desde volúmenes vacíos y alcanzó streaming en **12,795 s**.

La integración pasó **7 de 7** en **8,416 s**. La prueba de caída completó el CRUD con API A detenida y obtuvo **0 errores en 94 sondas**. El primer éxito después de confirmar la detención fue a los **0,135 s**.

| Fase | Sondas | p95 | Errores |
|---|---:|---:|---:|
| Base | 35 | 65,6 ms | 0 |
| Durante la inyección | 32 | 103,3 ms | 0 |
| API A detenida | 27 | 81,5 ms | 0 |

El ensayo de Operaciones observó la caída **9,953 s** después de confirmar la parada, conservó el evento tras reiniciar el monitor y observó API A operativa a los **23,860 s** desde el inicio del ensayo. El gateway temporal con el perfil HTTPS respondió HTTP 200 en `/api/ready` con **TLS 1.3** y certificado validado por el cliente.

El logotipo aportado por el usuario se sirvió en WebP de **24.922 bytes**. Edge comprobó la proporción 960 × 427 sin deformación, la vista a 390 y 1360 px y el favicon SVG. Se actualizó la captura de acceso en el ZIP local.

En el proyecto temporal de recuperación se aisló el primario, se comprobó HTTP 503, se promovió la réplica y se redirigieron los dos nodos y el monitor. Se confirmó una escritura a los **25,264 s** desde la orden de parada. Una réplica de reemplazo alcanzó streaming y recibió otra escritura a los **8,686 s** desde el inicio de su arranque. El pedido marcador ya estaba replicado antes de la parada. El ensayo automatizó las acciones de recuperación y usó un proyecto aparte.

### Acceso compacto y lanzador para Windows

La revisión final dejó una sola tarjeta de acceso y el monograma en el encabezado y el favicon. Se retiraron el pie y el arte panorámico de ambos accesos. El arte se conserva como recurso de identidad. Edge verificó escritorio a 1360 px y móvil a 390 px, un único título principal, formulario visible y ausencia de desbordamiento horizontal. Se renovaron siete capturas desde Docker con datos de demostración.

Se ejecutó el lanzador de Windows contra el proyecto local. Compose encontró los seis servicios y el lanzador confirmó HTTP 200 con estado ready antes de devolver la URL. Se creó y verificó el acceso directo del Escritorio, con destino resuelto desde el checkout que lo instaló y un icono ICO con el contorno angular rojo trazado a partir del arte Vayxer y exportado en tamaños de 16, 24, 32, 48, 64, 128 y 256 píxeles. El instalador vuelve a resolver las rutas si se ejecuta desde otra ubicación.

## Inicio guiado y autenticación por rol

Se verificó un arranque de Windows desde una carpeta sin configuración ni certificado y un proyecto Compose sin volúmenes. El lanzador generó ambos archivos de configuración HTTPS y alcanzó la provisión de cuentas. Se ejecutó el asistente de contraseñas mediante una terminal de prueba con eco desactivado. Tras cerrar y volver a levantar Compose, ambos roles conservaron sus contraseñas, el pedido de prueba seguía accesible y el certificado y la configuración coincidían byte por byte.

Pasaron **4 pruebas unitarias de autenticación y 7 de integración**. El tercer fallo devolvió HTTP 429 con Retry-After de cinco segundos. Un intento inmediato con la contraseña correcta siguió bloqueado. El siguiente se aceptó tras **5,28 s**. Las pruebas por HTTPS rechazaron cookies alteradas, rol falso, peticiones de otro origen y alta pública de cuentas. Confirmaron propiedad, expiración, logout y uso de la misma sesión desde ambas APIs. Operaciones autenticó a administración y mantuvo el historial con PostgreSQL detenido.

En Edge se verificaron el formulario único, el destino por rol, la cookie no legible desde JavaScript y el cierre de sesión. La confianza del certificado de prueba se limitó a su clave pública en el navegador de verificación. El asistente de Windows ofrece importar el certificado local solo con aceptación explícita.

## Controles de acceso y revisión de interfaz

Se verificó el control de cuentas en un laboratorio aislado. Pasaron **6 pruebas unitarias de autenticación y 8 de integración**. Los nombres existente e inexistente recibieron HTTP 401, 401 y 429 al tercer fallo. Cambiar la cookie conservó el bloqueo. Las comprobaciones posteriores se hicieron a los **5,422 s** y **5,437 s**, respectivamente. La sesión legítima previa siguió activa durante los fallos.

Solo administración pudo bloquear y desbloquear clientes. El bloqueo revocó la sesión en ambas APIs; desbloquear exigió volver a iniciar sesión. El servidor rechazó el bloqueo de administración, una acción enviada por cliente y un campo de rol añadido al cuerpo. Los eventos persistieron al reiniciar el monitor y excluyeron las contraseñas, cookies y direcciones de origen.

La regresión del balanceador observó ambos nodos. Con API A detenida, API B completó el CRUD. Hubo **0 errores en 85 sondas**, con p95 de **101,6 ms** en base, **97,2 ms** durante la inyección y **86,8 ms** con el nodo detenido. El primer éxito tras confirmar la parada fue a los **0,172 s**. Actividad de acceso siguió disponible con PostgreSQL detenido.

En el navegador se verificaron las confirmaciones y cancelación de cuentas, ambos temas, ambos roles y los anchos de **1360, 960 y 390 px**. Se ajustaron el tamaño mínimo de acciones, el ajuste de nombres largos y los campos de formularios en paneles estrechos. La arquitectura conserva sus componentes compartidos y los límites de capacidad descritos en el manual técnico.
