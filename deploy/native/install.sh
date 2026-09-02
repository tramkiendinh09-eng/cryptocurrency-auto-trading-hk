#!/usr/bin/env bash
#
# Native (non-Docker) installer for the DCA trading stack on Debian/Ubuntu.
#
# The upstream deployment path is Docker-only, and the repository's root
# compose.yaml points at build contexts (./frontend, ./backend) that do not
# exist. This script is the container-free alternative: MySQL, Redis and nginx
# come from apt, and the three application processes run under systemd.
#
#   ./install.sh bootstrap   create user/dirs/db, install units and nginx site
#   ./install.sh build       build the backend jar and the frontend bundle
#   ./install.sh deploy      copy build output into /opt/dca and restart services
#   ./install.sh schema      (re)load schema + seed into an EMPTY database
#   ./install.sh status      show what is running
#
# Everything is idempotent; re-running a step is safe. `schema` is the one
# exception and refuses to touch a database that already has trading rows.

set -euo pipefail

ROOT="/opt/dca"
SRC="${SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DB_NAME="${DB_NAME:-ai_trading}"
DB_USER="${DB_USER:-dca}"
SERVICES=(dca-backend dca-feed-adapter dca-worker)

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mfatal:\033[0m %s\n' "$*" >&2; exit 1; }

need_root() { [ "$(id -u)" = 0 ] || die "run as root"; }

cmd_bootstrap() {
  need_root
  log "creating service user and directory layout"
  id -u dca >/dev/null 2>&1 || useradd --system --home-dir "$ROOT" --shell /usr/sbin/nologin dca
  mkdir -p "$ROOT"/{app/backend,app/frontend,app/feed-adapter,app/python-worker,env,data/upload,logs,sql}
  chown -R dca:dca "$ROOT/data" "$ROOT/logs"
  chmod 750 "$ROOT/env"

  log "installing env templates (only if absent — existing secrets are kept)"
  for f in backend feed-adapter worker; do
    if [ ! -f "$ROOT/env/$f.env" ]; then
      cp "$SRC/deploy/native/env/$f.env.example" "$ROOT/env/$f.env"
      echo "    created $ROOT/env/$f.env — fill in the __CHANGE_ME__ values"
    fi
    chmod 600 "$ROOT/env/$f.env"
  done

  log "creating python venv"
  [ -d "$ROOT/venv" ] || python3 -m venv "$ROOT/venv"
  "$ROOT/venv/bin/pip" install -q --upgrade pip

  log "installing systemd units"
  cp "$SRC"/deploy/native/systemd/*.service /etc/systemd/system/
  systemctl daemon-reload

  log "installing nginx site"
  cp "$SRC/deploy/native/nginx-dca.conf" /etc/nginx/sites-available/dca
  ln -sf /etc/nginx/sites-available/dca /etc/nginx/sites-enabled/dca
  nginx -t && systemctl reload nginx

  log "bootstrap complete"
}

cmd_schema() {
  need_root
  local existing
  existing=$(mysql -N -B -e \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME';" 2>/dev/null || echo 0)
  if [ "${existing:-0}" -gt 0 ] && [ "${FORCE:-0}" != "1" ]; then
    die "$DB_NAME already has $existing tables. These scripts DROP tables; \
re-running them on a live database destroys order and audit history. \
Set FORCE=1 only if you know the database is disposable."
  fi
  log "loading schema into $DB_NAME"
  mysql "$DB_NAME" < "$SRC/sql/ruoyi_boot_min.sql"
  mysql "$DB_NAME" < "$SRC/sql/trade_runtime_boot_min.sql"
  log "loading seed data"
  [ -f "$ROOT/sql/seed_applied.sql" ] \
    || die "expected $ROOT/sql/seed_applied.sql (seed_min.sql with placeholders substituted)"
  mysql "$DB_NAME" < "$ROOT/sql/seed_applied.sql"
  log "schema + seed loaded"
}

cmd_build() {
  log "building backend jar"
  ( cd "$SRC" && mvn -q -pl ruoyi-admin -am -DskipTests package )
  log "building frontend bundle"
  ( cd "$SRC/dca-ui" && npm ci --no-audit --no-fund && npm run build:prod )
  log "build complete"
}

cmd_deploy() {
  need_root
  log "stopping services"
  systemctl stop "${SERVICES[@]}" 2>/dev/null || true

  log "deploying backend jar"
  local jar
  jar=$(ls -1 "$SRC"/ruoyi-admin/target/*.jar 2>/dev/null | grep -v sources | head -1) \
    || die "no jar in ruoyi-admin/target — run '$0 build' first"
  install -m 644 "$jar" "$ROOT/app/backend/app.jar"

  log "deploying frontend bundle"
  [ -d "$SRC/dca-ui/dist" ] || die "no dca-ui/dist — run '$0 build' first"
  rm -rf "$ROOT/app/frontend"
  mkdir -p "$ROOT/app/frontend"
  cp -r "$SRC/dca-ui/dist/." "$ROOT/app/frontend/"

  log "deploying python components"
  rsync -a --delete --exclude '__pycache__' --exclude '.venv' --exclude 'tests' \
    "$SRC/feed-adapter/" "$ROOT/app/feed-adapter/"
  rsync -a --delete --exclude '__pycache__' --exclude '.venv' --exclude 'tests' \
    "$SRC/python-worker/" "$ROOT/app/python-worker/"

  log "installing python dependencies"
  "$ROOT/venv/bin/pip" install -q -r "$ROOT/app/python-worker/requirements.txt"
  "$ROOT/venv/bin/pip" install -q -r "$ROOT/app/feed-adapter/requirements.txt"

  chown -R dca:dca "$ROOT/app"
  chmod -R go-w "$ROOT/app"

  log "starting services"
  systemctl enable --now "${SERVICES[@]}"
  cmd_status
}

cmd_status() {
  for s in "${SERVICES[@]}"; do
    printf '%-22s %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null || echo inactive)"
  done
  echo
  echo "listeners:"
  ss -tlnp 2>/dev/null | grep -E '18080|18081|8099' || echo "  (none yet)"
}

case "${1:-}" in
  bootstrap) cmd_bootstrap ;;
  build)     cmd_build ;;
  deploy)    cmd_deploy ;;
  schema)    cmd_schema ;;
  status)    cmd_status ;;
  *) sed -n '3,20p' "$0"; exit 1 ;;
esac
