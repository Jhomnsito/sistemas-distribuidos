# Guía breve para el profesor

## Abrir Vayxer

1. Instale y abra Docker Desktop con contenedores Linux. Descomprima el proyecto en una carpeta permanente.
2. Ejecute **Vayxer.cmd**. El primer inicio prepara el certificado HTTPS local y le pide definir dos contraseñas con entrada oculta. El lanzador verifica el certificado local y pide aceptación explícita antes de agregarlo al almacén de confianza de su usuario de Windows. Después abre Microsoft Edge con un perfil separado, sin opciones para ignorar errores HTTPS.
3. Use **Instalar acceso directo.cmd** para abrir Vayxer desde el Escritorio en adelante. El panel se abre después de que Docker confirme disponibilidad.

| Cuenta | Qué demostrar |
|---|---|
| `esteban_cliente` | Crear un pedido y consultar sus propios registros |
| `esteban_admin` | Consultar todos los pedidos, cambiar un estado y revisar Operaciones |

Las contraseñas se definen en el equipo del evaluador. No hay autorregistro. Las cuentas de cliente requieren letras y símbolos. La de administración requiere números y símbolos. El mínimo es de 12 caracteres.

## Revisión de fallos

- En el formulario, pruebe dos contraseñas incorrectas. La tercera activa el bloqueo de cinco segundos. Un intento inmediato sigue bloqueado. Después de cinco segundos, la contraseña correcta vuelve a funcionar.
- Para probar roles, abra una ventana privada y acceda como cliente. Ese rol no puede entrar en Operaciones ni modificar pedidos por la API.
- Con la sesión de administración abierta, ejecute `docker compose stop api-a` en la carpeta del proyecto. En Operaciones, espere la detección del fallo y compruebe que la otra API atiende pedidos. Termine con `docker compose start api-a`.
- Para cerrar el laboratorio conservando sus datos, ejecute `docker compose -f compose.yaml -f tls.compose.yaml down`. Abra **Vayxer.cmd** para continuar la demostración.

Consulte el [README](../README.md) para las pruebas automatizadas y el [informe](informe.md) para los resultados medidos.
