#!/usr/bin/env bash
(
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v app_password="$APP_PASSWORD" -v repl_password="$REPL_PASSWORD" <<'SQL'
CREATE ROLE orders_app LOGIN PASSWORD :'app_password';
CREATE ROLE orders_repl LOGIN REPLICATION PASSWORD :'repl_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
\i /opt/pedidos/schema.sql
GRANT SELECT, INSERT, UPDATE, DELETE ON orders TO orders_app;
GRANT SELECT, INSERT, UPDATE ON request_log TO orders_app;
\i /opt/pedidos/02-security.sql
SQL
echo 'host replication orders_repl all scram-sha-256' >> "$PGDATA/pg_hba.conf"
)
