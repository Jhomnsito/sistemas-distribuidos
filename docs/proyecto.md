# Plan del equipo y trazabilidad · Vayxer

Entrega prevista el **19 de noviembre de 2026**. El enunciado menciona tres semanas y describe dos. Se usa la fecha de entrega como límite y dos ventanas de trabajo. El equipo puede adaptar el reparto una vez confirmados los integrantes.

| Épica / tarea | Responsable sugerido | Depende de | Criterio de aceptación | Ventana |
|---|---|---|---|---|
| E1 · Contrato REST y esquema | Integrante A | Requisitos | CRUD, versiones, estados y errores documentados | 5–9 nov |
| E1 · Validación y autorización | Integrante A | Contrato | Rechazo 401 y 422 comprobado; rol SQL de alcance acotado | 5–9 nov |
| E1 · Concurrencia e idempotencia | Integrante A | Esquema | Reintentos concurrentes devuelven una sola creación; una edición obsoleta devuelve 409 | 7–11 nov |
| E2 · Despliegue base y redes | Integrante B | Contrato | Gateway único, dos APIs y puertos de BD internos | 5–9 nov |
| E2 · Réplica y procedimiento de promoción | Integrante B | Despliegue | Demostración de convergencia y escritura en el nodo promovido tras aislar el anterior | 8–14 nov |
| E2 · Inyección y mediciones | Integrante B, apoyo D | Despliegue | Publicar muestras, p95, error y recuperación medidos | 12–16 nov |
| E3 · Panel, formularios y feedback | Integrante C | Contrato | Flujo CRUD funcional, accesible por teclado y responsive | 6–12 nov |
| E3 · Capturas y manual de usuario | Integrante C | Panel estable | Evidencia desktop, móvil, creación y confirmación | 12–16 nov |
| E4 · Unitarias, integración y revisión cruzada | Integrante D o equipo | E1–E3 | Al menos tres pruebas de cada tipo, con salida real | 13–17 nov |
| E4 · Ensayo, informe y entrega | Equipo | Pruebas y documentación | Revisar ZIP, despliegue limpio, historial y demo | 17–19 nov |

Para tres integrantes, D se reparte entre A, B y C. Cada persona utiliza una rama, abre una revisión y registra al menos tres commits de contenido real con su propia identidad. Ejemplos de unidades para dividir aportes:

- A · contrato y esquema, validación/autorización, transacciones y pruebas de dominio.
- B · Compose y redes, réplica, recuperación y sonda de disponibilidad.
- C · estructura visual, formularios y estados, accesibilidad y manual de usuario.
- D · pruebas de integración, análisis de métricas, trazabilidad y revisión de empaquetado.

El repositorio es [Jhomnsito/sistemas-distribuidos](https://github.com/Jhomnsito/sistemas-distribuidos). El equipo debe usar ramas por tarea y revisar contribuciones con `git shortlog -sne --all` y `git log --oneline --all`. La revisión final debe comprobar las contribuciones sustantivas por integrante. Los commits de la entrega inicial no cuentan como contribuciones de los integrantes. El requisito se comprueba con trabajo real del equipo.

## Matriz de trazabilidad

| Nº | Criterio del enunciado o ampliación pedida | Implementación | Evidencia |
|---:|---|---|---|
| 1 | Web en React, HTML5, CSS3 y JavaScript | `frontend` | Build y capturas de escritorio y móvil |
| 2 | Python, comunicación REST y dos nodos | `backend`, `compose.yaml`, `deploy/gateway.conf` | Prueba que observa ambos IDs por NGINX |
| 3 | CRUD y cuatro estados | API y panel | Integración con alta, tres avances y borrado |
| 4 | PostgreSQL, persistencia y replicación | Esquema, volumen y streaming WAL | Consultas directas a la réplica durante CRUD |
| 5 | Tolerancia ante fallos simulados | NGINX, reintentos e idempotencia | CRUD con una API detenida; p95 y error medidos |
| 6 | Seguridad, identidad y propiedad | Roles, filtros de servidor, AES-GCM y HTTPS obligatorio para iniciar sesión | Clientes aislados, 403 de Operaciones, SQL de texto cifrado, unitarias de manipulación |
| 7 | Fallos observables y recuperación | Monitor, auditoría y promoción | Eventos persistentes, indisponibilidad de base y procedimiento ensayado |
| 8 | Pruebas unitarias y de integración | `tests` | Informe y evidencia de ejecución |
| 9 | Código por componentes y manuales con diagramas y capturas | README y `docs` | Instalación, arquitectura, procedimientos y capturas |
| 10 | Repositorio colaborativo y al menos tres commits por persona | Flujo de ramas y revisiones anterior | Pendiente de contribuciones reales del equipo |
