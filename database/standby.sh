#!/usr/bin/env bash
set -euo pipefail
if [[ ! -s "$PGDATA/PG_VERSION" ]]; then
  # El volumen es exclusivo de este nodo. El staging evita usar copias incompletas.
  install -d -m 700 -o postgres -g postgres "$PGDATA"
  staging="$PGDATA/.bootstrap"
  rm -rf -- "$staging"
  install -d -m 700 -o postgres -g postgres "$staging"
  gosu postgres env PGPASSWORD="$REPL_PASSWORD" pg_basebackup \
    -h "$REPL_SOURCE" -U orders_repl -D "$staging" -X stream -R --no-password
  # Guardar la contraseña en .pgpass, fuera de los parámetros de conexión.
  sed -i '/^primary_conninfo/d' "$staging/postgresql.auto.conf"
  escaped=${REPL_PASSWORD//\\/\\\\}
  escaped=${escaped//:/\\:}
  printf '%s:5432:replication:orders_repl:%s\n' "$REPL_SOURCE" "$escaped" > "$staging/.pgpass"
  chown postgres:postgres "$staging/.pgpass"
  chmod 600 "$staging/.pgpass"
  printf "primary_conninfo = 'host=%s user=orders_repl passfile=%s/.pgpass application_name=replica'\n" \
    "$REPL_SOURCE" "$PGDATA" >> "$staging/postgresql.auto.conf"
  # PG_VERSION marca la finalización. Un reinicio con archivos parciales se detiene.
  find "$PGDATA" -mindepth 1 -maxdepth 1 ! -name .bootstrap | grep -q . && exit 1
  find "$staging" -mindepth 1 -maxdepth 1 ! -name PG_VERSION -exec mv -t "$PGDATA" -- {} +
  mv "$staging/PG_VERSION" "$PGDATA/"
  rmdir "$staging"
fi
exec docker-entrypoint.sh postgres -c wal_level=replica -c wal_keep_size=256MB
