# Vayxer · Sistema distribuido de gestión de pedidos tolerante a fallos

Proyecto final académico. Panel React en español, dos APIs FastAPI detrás de NGINX, PostgreSQL con réplica física asíncrona y un monitor con historial persistente.

## Inicio rápido en Windows

1. Instala Docker Desktop con contenedores Linux. Descomprime el ZIP o clona el repositorio en una carpeta permanente.
2. Ejecuta **Vayxer.cmd**. La primera vez prepara HTTPS y pide las contraseñas de `esteban_cliente` y `esteban_admin` con entrada oculta. Antes de abrir Microsoft Edge, verifica el certificado servido y la API. Si el certificado aún no es de confianza, muestra su huella y pide escribir `SI` para importar únicamente ese certificado al almacén del usuario actual de Windows. Edge usa un perfil separado, sin opciones para ignorar errores de certificados.
3. Opcionalmente, ejecuta **Instalar acceso directo.cmd**. Después usa **Vayxer** en el Escritorio. Si mueves la carpeta, vuelve a crear el acceso directo.

[Guía breve](docs/guia-profesor.md)

## Despliegue manual

Requisitos: Docker con Compose 2.24.4 o posterior, Python 3.11+ y un navegador. Ejecuta desde la raíz.

```sh
python deploy/setup.py
# Prepara local-tls/cert.pem y local-tls/key.pem según el manual técnico.
docker compose -f compose.yaml -f tls.compose.yaml config --quiet
docker compose -f compose.yaml -f tls.compose.yaml up -d --build --wait
```

Aprovisiona las dos cuentas iniciales desde una terminal en la carpeta del proyecto. Cada comando solicita y confirma la contraseña sin mostrarla.

```sh
docker compose exec monitor python auth_store.py esteban_cliente
docker compose exec monitor python auth_store.py esteban_admin
```

Usa **https://127.0.0.1:8443** con un certificado de confianza para el navegador. Hay un solo formulario. El servidor determina el rol a partir de la cuenta. Los clientes crean y consultan sus pedidos. Administración entra en **Operaciones** y puede volver a la gestión de pedidos. Para dar de alta otro cliente, un operador autorizado de Docker ejecuta el mismo comando con el nuevo nombre de usuario. Volver a ejecutar el comando para una cuenta existente cambia su contraseña y revoca sus sesiones.

Conserva `.env` y una copia protegida de `DATA_KEY` entre reinicios. Para actualizar una instalación previa con datos, sigue el [procedimiento de migración](docs/manual-tecnico.md#migración-de-una-instalación-previa). Usa el [perfil HTTPS](docs/manual-tecnico.md#https-local). La primera compilación requiere acceso a los registros de imágenes, npm y PyPI.

```sh
docker compose exec -T replica psql -U postgres -d pedidos -c "SELECT pg_is_in_recovery(), status FROM pg_stat_wal_receiver"
curl --cacert local-tls/cert.pem https://127.0.0.1:8443/api/ready
```

`docker compose down` conserva datos. Para promover y recuperar PostgreSQL, sigue el [manual técnico](docs/manual-tecnico.md#recuperación-manual-del-primario-en-compose).

## Pruebas

```sh
python -m pip install -r backend/requirements.txt
python -m unittest discover -s tests -p test_domain.py -v
python -m unittest discover -s tests -p test_vault.py -v
python -m unittest discover -s tests -p test_auth_store.py -v
python -m unittest discover -s tests -p test_tls_verify.py -v
```

Usa un laboratorio aislado. Aprovisiona también `cliente_pruebas` en ese laboratorio para la prueba de propiedad. Las pruebas piden las contraseñas interactivamente. En PowerShell, desde la raíz:

```powershell
$env:SSL_CERT_FILE = (Resolve-Path local-tls/cert.pem).Path
python -m unittest discover -s tests -p test_integration.py -v
python tests/fault.py
python tests/ops_fault.py
```

Si cambias el puerto, configura `TEST_URL` con la URL base. Las pruebas de fallo detienen `api-a` y vuelven a iniciarlo. La prueba de Operaciones también reinicia el monitor para verificar que conserva los eventos.

## Material de entrega

Las siete capturas del manual se distribuyen solo en el ZIP de entrega, en `Pedidos/docs/capturas`. No se publican imágenes de demostración en este repositorio.

- [Manual de usuario](docs/manual-usuario.md)
- [Manual técnico](docs/manual-tecnico.md)
- [Informe de pruebas](docs/informe.md)
- [Backlog y matriz de trazabilidad](docs/proyecto.md)
