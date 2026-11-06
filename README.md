# Vayxer · Sistema distribuido de gestión de pedidos tolerante a fallos

Proyecto final académico. Panel React en español, dos APIs FastAPI detrás de NGINX, PostgreSQL con réplica física asíncrona y un monitor con historial persistente.

## Acceso directo en Windows

Descomprime el ZIP o clona el repositorio en una carpeta permanente. Ejecuta **Instalar acceso directo.cmd** para crear **Vayxer** en el Escritorio, o abre **Vayxer.cmd** desde la carpeta. Docker Desktop debe estar instalado con contenedores Linux y Compose. El primer inicio requiere Python 3.11 o posterior si aún no existe `.env`. El lanzador espera una respuesta real de la API antes de abrir el navegador. Si mueves la carpeta, vuelve a crear el acceso directo desde su nueva ubicación.

## Despliegue local

Requisitos: Docker con Compose v2, Python 3.11+ y un navegador. Ejecuta desde la raíz.

```sh
python deploy/setup.py
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
```

Abre **http://127.0.0.1:8080**. En `.env`, `APP_TOKEN` es la clave de administración. `CLIENT_TOKENS` contiene una clave individual para cada cliente de demostración, `demo-alba` y `demo-bruno`. Copia solamente el valor de la clave correspondiente. Los clientes crean y consultan sus pedidos. Administración gestiona todos los pedidos y accede a **Operaciones**, en `/operaciones`, con autenticación separada en la interfaz y control del lado servidor.

Conserva `.env` y una copia protegida de `DATA_KEY` entre reinicios. Para actualizar una instalación previa con datos, sigue el [procedimiento de migración](docs/manual-tecnico.md#migración-de-una-instalación-previa). Para HTTPS local, usa el [perfil TLS](docs/manual-tecnico.md#https-local-opcional). La primera compilación requiere acceso a los registros de imágenes, npm y PyPI.

```sh
docker compose exec -T replica psql -U postgres -d pedidos -c "SELECT pg_is_in_recovery(), status FROM pg_stat_wal_receiver"
curl http://127.0.0.1:8080/api/ready
```

`docker compose down` conserva datos. Para promover y recuperar PostgreSQL, sigue el [manual técnico](docs/manual-tecnico.md#recuperación-manual-del-primario-en-compose).

## Pruebas

```sh
python -m pip install -r backend/requirements.txt
python -m unittest discover -s tests -p test_domain.py -v
python -m unittest discover -s tests -p test_vault.py -v
```

Usa un laboratorio aislado. En PowerShell, desde la raíz:

```powershell
$env:APP_TOKEN = (Get-Content .env | Where-Object { $_ -like 'APP_TOKEN=*' }).Substring(10)
$env:CLIENT_TOKENS = (Get-Content .env | Where-Object { $_ -like 'CLIENT_TOKENS=*' }).Substring(14).Trim("'")
python -m unittest discover -s tests -p test_integration.py -v
python tests/fault.py
python tests/ops_fault.py
```

Si cambias el puerto, configura `TEST_URL` con la URL base. Las pruebas de fallo detienen `api-a` y vuelven a iniciarlo. La prueba de Operaciones también reinicia el monitor para verificar que conserva los eventos.

## Material de entrega

- [Manual de usuario](docs/manual-usuario.md)
- [Manual técnico](docs/manual-tecnico.md)
- [Informe de pruebas](docs/informe.md)
- [Backlog y matriz de trazabilidad](docs/proyecto.md)
