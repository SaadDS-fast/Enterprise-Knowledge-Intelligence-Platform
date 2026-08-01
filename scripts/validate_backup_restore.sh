#!/bin/sh
set -eu

compose="docker compose${E2E_COMPOSE_FILES:+ $E2E_COMPOSE_FILES}"
restore_db="ekip_restore_$$"
dump_path="/tmp/ekip-enterprise-$$.dump"

cleanup() {
  $compose exec -T postgres rm -f "$dump_path" >/dev/null 2>&1 || true
  $compose exec -T postgres dropdb -U ekip --if-exists "$restore_db" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

source_counts="$($compose exec -T postgres psql -U ekip -d ekip -Atc \
  "select (select count(*) from organizations)||','||(select count(*) from workspaces)||','||
  (select count(*) from documents)||','||(select count(*) from chunks);")"
$compose exec -T postgres pg_dump -U ekip -d ekip -Fc -f "$dump_path"
$compose exec -T postgres createdb -U ekip "$restore_db"
$compose exec -T postgres pg_restore -U ekip -d "$restore_db" --no-owner "$dump_path"
$compose run --rm -e "DATABASE_URL=postgresql+asyncpg://ekip:ekip@postgres:5432/$restore_db" \
  backend alembic downgrade -1 >/dev/null
$compose run --rm -e "DATABASE_URL=postgresql+asyncpg://ekip:ekip@postgres:5432/$restore_db" \
  backend alembic upgrade head >/dev/null
$compose run --rm -e "DATABASE_URL=postgresql+asyncpg://ekip:ekip@postgres:5432/$restore_db" \
  backend alembic check >/dev/null
restored_counts="$($compose exec -T postgres psql -U ekip -d "$restore_db" -Atc \
  "select (select count(*) from organizations)||','||(select count(*) from workspaces)||','||
  (select count(*) from documents)||','||(select count(*) from chunks);")"

test "$source_counts" = "$restored_counts"

$compose run --rm --entrypoint /bin/sh minio-init -c '
  mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
  permission="$(mc anonymous get "local/$OBJECT_STORAGE_BUCKET")"
  case "$permission" in *private*) ;; *) exit 1 ;; esac
  mc find "local/$OBJECT_STORAGE_BUCKET" >/dev/null
'

printf '{"database_counts":"%s","restored_counts":"%s","database_restore":true,"downgrade_upgrade_cycle":true,"minio_private_and_readable":true}\n' \
  "$source_counts" "$restored_counts"
