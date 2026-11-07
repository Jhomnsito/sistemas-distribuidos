# Manual de usuario · Vayxer

Las siete capturas se incluyen exclusivamente en el ZIP de entrega, dentro de `Pedidos/docs/capturas`. El repositorio público conserva este manual sin publicar las imágenes.

## Instalación y acceso

En Windows, instala Docker Desktop con contenedores Linux y descomprime el proyecto en una carpeta permanente. Ejecuta **Vayxer.cmd**. El primer inicio prepara HTTPS y solicita las contraseñas iniciales con entrada oculta. Antes de abrir Edge, verifica el certificado local y pide aceptación para agregarlo al almacén de confianza de tu usuario de Windows. Escribe `SI` solo si autorizas ese cambio. En los siguientes inicios conserva la configuración.

Ejecuta **Instalar acceso directo.cmd** para abrir Vayxer desde el Escritorio. Si mueves la carpeta, vuelve a crear el acceso directo. Para otros entornos, sigue el [despliegue manual del README](../README.md#despliegue-manual).

Abre **https://127.0.0.1:8443**, escribe usuario y contraseña y pulsa **Entrar al panel**. El servidor determina el rol de la cuenta. Tres fallos consecutivos producen una pausa de cinco segundos para ese nombre de usuario. Las sesiones ya abiertas siguen funcionando.

Captura 1 del paquete: Acceso con usuario y contraseña.

## Consultar y registrar

Cada cliente consulta sus propios pedidos. Administración puede ver todos, incluidos los registros anteriores a las cuentas.

- **Actualizar** vuelve a consultar la página. El cliente ve el estado de conexión; administración también ve qué nodo respondió a la última consulta válida.
- La búsqueda y el selector filtran los pedidos cargados. Usa **Anterior** o **Siguiente** para consultar otras páginas.
- **Nuevo pedido** abre el formulario. Escribe cliente, producto y unidades de 1 a 999. **Guardar pedido** crea el registro en estado **Pendiente**.

Captura 2 del paquete: Registro de pedidos con datos ficticios.

Captura 3 del paquete: Formulario de creación.

## Editar y eliminar como administrador

- El lápiz permite corregir datos y avanzar un estado: **Pendiente → En proceso → Enviado → Entregado**.
- La papelera abre una confirmación. Revisa cliente y producto antes de pulsar **Eliminar pedido**.
- Si otro operador cambió el registro, cierra el formulario, actualiza y vuelve a abrirlo.
- Si una operación no pudo confirmarse, **Reintentar** conserva la misma solicitud. Si eliges **Cerrar y actualizar**, revisa el registro antes de crear otro pedido.

Captura 4 del paquete: Confirmación de borrado de un pedido ficticio.

En pantallas pequeñas, los pedidos se presentan como fichas con sus acciones.

Captura 5 del paquete: Gestión de pedidos en móvil.

## Operaciones y cuentas cliente

Administración puede abrir **Operaciones** con su misma sesión. La página presenta la última sonda de cada servicio, cambios de salud, auditoría de pedidos sin datos personales y actividad de acceso.

Captura 6 del paquete: Salud e historial de operaciones.

En **Cuentas cliente**, **Bloquear** requiere confirmación y revoca todas las sesiones de esa cuenta. **Desbloquear** permite un nuevo inicio de sesión con la misma contraseña. Las cuentas administrativas no pueden bloquearse desde esta función.

Si cae una API, la otra puede atender pedidos. Si PostgreSQL queda inaccesible, el CRUD se suspende y Operaciones conserva salud y actividad de acceso mientras gateway y monitor respondan. Si cae el monitor, no se pueden validar sesiones. Si cae el gateway, espera su recuperación.

Pulsa **Cerrar sesión** al terminar. El servidor revoca la sesión y elimina la cookie protegida; JavaScript no puede leerla. `docker compose -f compose.yaml -f tls.compose.yaml down` apaga el laboratorio conservando los datos.

## Capturas e identidad

Las capturas del 6 de noviembre de 2026 usan datos ficticios. Las figuras 2 a 6 corresponden a la revisión previa del panel y conservan el monograma anterior; documentan el flujo CRUD, no las nuevas vistas de control de cuentas. Las figuras 1 y 7 muestran el acceso actualizado con la flecha angular y el selector de tema. La interfaz actual admite modo claro y oscuro y conserva la preferencia local.

Captura 7 del paquete: Acceso actualizado en móvil.

El [arte panorámico](identidad/vayxer-art.webp) se conserva como recurso de identidad. El encabezado, favicon y acceso directo usan la flecha angular.

| Captura | Archivo dentro de `Pedidos/docs/capturas` |
|---|---|
| 1 · Acceso | `01-acceso.png` |
| 2 · Registro de pedidos | `02-panel.png` |
| 3 · Formulario de creación | `03-nuevo.png` |
| 4 · Confirmación de borrado | `04-confirmar.png` |
| 5 · Gestión en móvil | `05-movil.png` |
| 6 · Operaciones | `06-operaciones.png` |
| 7 · Acceso en móvil | `07-acceso-movil.png` |
