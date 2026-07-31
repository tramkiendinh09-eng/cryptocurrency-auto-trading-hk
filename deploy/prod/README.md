# web4-first Production Deployment

Target directory: `/opt/web4-first`

## Layout

- `compose.yaml`
- `frontend/`
  - `Dockerfile`
  - `nginx.conf`
  - `dist/`
- `backend/`
  - `Dockerfile`
  - `app.jar`
  - `.env`
- `feed-adapter/`
  - `Dockerfile`
  - `app.py`
  - `requirements.txt`
  - `feed_adapter/`
  - `.env`
- `python-worker/`
  - `Dockerfile`
  - `requirements.txt`
  - `main.py`
  - `core/`
  - `modules/`
  - `trade_runtime/`
  - `.env`
- `nginx/dca.example.conf`（部署时复制为 `your-domain.conf` 并替换 `<your-domain>`）
- `data/upload/`

## Build Artifacts

### 1. Frontend

```bash
cd dca-ui
npm install
npm run build:prod
```

### 2. Backend

```bash
mvn -pl ruoyi-admin -am -DskipTests package
```

## Server Preparation

1. Copy `deploy/prod/*` to `/opt/web4-first`.
2. Copy `dca-ui/dist` to `/opt/web4-first/frontend/dist`.
3. Copy the built backend jar from `ruoyi-admin/target` to `/opt/web4-first/backend/app.jar`.
4. Copy `feed-adapter/app.py`, `feed-adapter/requirements.txt`, and `feed-adapter/feed_adapter` to `/opt/web4-first/feed-adapter/`.
5. Copy `python-worker/main.py`, `python-worker/requirements.txt`, `python-worker/core`, `python-worker/modules`, and `python-worker/trade_runtime` to `/opt/web4-first/python-worker/`.
6. Copy `backend/.env.example` to `backend/.env`, copy `feed-adapter/.env.example` to `feed-adapter/.env`, copy `python-worker/.env.example` to `python-worker/.env`, then fill in the real values.
7. Create the upload directory: `mkdir -p /opt/web4-first/data/upload`.

## Database Bootstrap

The repository keeps only two bootstrap SQL files. Execute them in order before starting the runtime stack in a fresh or rebuilt environment:

- `sql/ruoyi_boot_min.sql`
- `sql/trade_runtime_boot_min.sql`

`sql/ruoyi_boot_min.sql` contains the minimal RuoYi framework tables plus the current trade control-plane menus.

`sql/trade_runtime_boot_min.sql` contains the automated-trading runtime tables, audit/replay tables, WebSocket market source seed, exchange account seed, and the current event-gated runtime policy seed.

Do not re-import these scripts into an already initialized production database. For an existing environment, reconcile the live schema and seed data against these two bootstrap scripts first, then start the worker.

## Runtime Notes

- `feed-adapter` exposes `/health`, `/runtime/news`, `/runtime/social`, and `/runtime/onchain`.
- The initial onchain adapter returns `ready` with an empty item set, which keeps the runtime from treating the source as missing infrastructure.
- Keep source-level refresh intervals aligned with source cadence: `FEED_ADAPTER_NEWS_MIN_REFRESH_SECONDS=180`, `FEED_ADAPTER_ONCHAIN_MIN_REFRESH_SECONDS=300`, `FEED_ADAPTER_SOCIAL_MIN_REFRESH_SECONDS=300` unless you have a stronger upstream SLA.
- Point `market_api_config.api_url` for IDs `102`, `103`, and `104` at `http://feed-adapter:18080/runtime/news`, `http://feed-adapter:18080/runtime/onchain`, and `http://feed-adapter:18080/runtime/social`.
- `python-worker/main.py` now defaults to `trade_runtime`.
- Keep `WORKER_PROFILE=trade_runtime` in production unless you are explicitly starting the frozen legacy worker.
- Keep `TRADE_RUNTIME_RUN_MODE=forever` for the long-running production worker.
- The runtime worker also consumes queued `TRADE_RUNTIME_REPLAY` tasks while running in `forever` mode.
- Set `REDIS_HOST` / `TRADE_RUNTIME_REDIS_HOST` to the real reachable production Redis host instead of relying on Docker Desktop-only host aliases.
- Set `TRADE_RUNTIME_BASE_URL`, runtime Redis settings, and runtime bearer token in `python-worker/.env`.
- Runtime business configuration and exchange accounts are read from Java bootstrap and database tables, not from Python worker environment variables.
- `TRADE_RUNTIME_REPLAY_TRACE_ID` stays empty in the long-running worker; only set it when you intentionally start a one-shot replay process with `TRADE_RUNTIME_RUN_MODE=replay`.

## Replay Operations

For normal production deployment, keep a single long-running worker with:

```env
WORKER_PROFILE=trade_runtime
TRADE_RUNTIME_RUN_MODE=forever
TRADE_RUNTIME_REPLAY_TRACE_ID=
```

If you need to run a one-shot direct replay process manually, override the runtime mode:

```bash
docker compose run --rm \
  -e WORKER_PROFILE=trade_runtime \
  -e TRADE_RUNTIME_RUN_MODE=replay \
  -e TRADE_RUNTIME_REPLAY_TRACE_ID=<source-trace-id> \
  python-worker
```

The normal operator path is still the Replay Console / `/dca/trade/replay/dispatch`, which queues a `TRADE_RUNTIME_REPLAY` task for the forever worker.

## Start

```bash
cd /opt/web4-first
docker compose up -d --build
```
