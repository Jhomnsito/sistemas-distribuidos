# Manual de usuario · Vayxer

Las capturas de demostración se incluyen en el ZIP de entrega.

## Instalación y acceso

En Windows puedes usar **Instalar acceso directo.cmd** y abrir **Vayxer** desde el Escritorio. La primera vez, el lanzador prepara HTTPS y pide las contraseñas de las cuentas iniciales con entrada oculta. En las siguientes visitas conserva la configuración y abre el panel cuando la API confirma que está disponible.

1. Descomprime la entrega y abre una terminal en la carpeta `Pedidos`.
2. Genera la configuración con `python deploy/setup.py`.
3. Prepara el perfil HTTPS y aprovisiona las cuentas según el README.
4. Abre **https://127.0.0.1:8443**. Escribe tu usuario y contraseña y pulsa **Entrar al panel**. El servidor selecciona tu vista según tu cuenta.


## Consultar y registrar

Cada cliente ve sus propios pedidos. Administración puede ver todos, incluidos los registros anteriores a la incorporación de cuentas.

- El registro muestra los pedidos recientes y el nodo que respondió a la última consulta exitosa. **Actualizar** vuelve a consultar la página.
- Usa la búsqueda para encontrar un cliente, producto o identificador. Las tarjetas y el selector filtran los pedidos cargados en la página actual. Usa **Anterior** o **Siguiente** para consultar otras páginas.
- Pulsa **Nuevo pedido**. Escribe cliente, producto y unidades de 1 a 999. **Guardar pedido** crea un registro en estado **Pendiente**.



## Editar y eliminar como administrador

- Pulsa el lápiz de la fila. Puedes corregir los datos y avanzar un estado. El flujo es **Pendiente → En proceso → Enviado → Entregado**. Pulsa **Guardar pedido**.
- Para eliminar, pulsa la papelera, revisa el cliente y producto y confirma con **Eliminar pedido**.
- Si otro operador modificó el pedido, cierra el formulario, actualiza y vuelve a abrirlo.
- Si el panel no pudo confirmar una operación, usa **Reintentar** para consultar el resultado de la misma solicitud. Si eliges **Cerrar y actualizar**, revisa el registro antes de volver a crear el pedido.


En pantallas pequeñas, cada pedido se organiza como una ficha con el estado, las unidades, la fecha y las acciones de editar y eliminar a la vista.


Pulsa **Cerrar sesión** al terminar. El token permanece en memoria mientras el panel está abierto. Para apagar el laboratorio, ejecuta `docker compose down`.

## Operaciones

En el panel de pedidos, administración puede abrir **Operaciones** con su misma sesión. La página muestra la última sonda de cada servicio, el historial de cambios de salud y la actividad de pedidos sin datos personales.


Si una API se detiene, puedes seguir registrando y consultando pedidos mediante la API sana. Si la base queda inaccesible, la actividad de pedidos se suspende y Operaciones conserva el historial de salud mientras el gateway y el monitor respondan. Si cae el gateway, espera su recuperación antes de volver a abrir el panel.

El [arte panorámico de Vayxer](identidad/vayxer-art.webp) se conserva como recurso de identidad. La interfaz usa el monograma en el encabezado y en el favicon.

Si fallas tres veces seguidas al ingresar la contraseña, espera cinco segundos antes de volver a intentarlo.


## Actividad de acceso y cuentas cliente

En Operaciones, administración puede consultar «Actividad de acceso» y revisar la lista de cuentas. «Bloquear» pide confirmación y cierra las sesiones de esa cuenta. «Desbloquear» permite que el cliente vuelva a iniciar sesión. La contraseña se conserva. Las cuentas de administración están protegidas contra esta acción.

Los tres fallos de contraseña producen una pausa temporal de cinco segundos para ese nombre de usuario. Las sesiones que ya estaban abiertas siguen funcionando. La pausa no depende de la dirección IP ni se reinicia al cambiar cookies.
