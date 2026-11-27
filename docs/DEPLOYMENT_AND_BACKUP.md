# VYRO-X — Production Deployment, PostgreSQL Migrations & Backup Runbook

## 1. Production Safety Guards
When `ENVIRONMENT=production` is set in the backend environment:
- **No Silent SQLite Fallback:** Startup fails loudly (`RuntimeError`) if `DATABASE_URL` is unset or points to SQLite.
- **Strong JWT Secret Required:** Startup fails loudly if `JWT_SECRET_KEY` is the development default or shorter than 32 characters.
- **Automatic URL Normalization:** `postgres://` and `postgresql://` connection strings from managed providers (Render, Railway, Neon, Supabase) are normalized to `postgresql+psycopg2://`.

---

## 2. Option A — Cloud Deployment (Render Backend + Vercel Frontend)

### Backend + Managed PostgreSQL (Render)
1. Push the repository to GitHub and connect it in Render via **New → Blueprint** using `render.yaml` (or create a Web Service pointing to `backend/Dockerfile` + a Managed PostgreSQL database).
2. Configure environment variables:
   - `ENVIRONMENT=production`
   - `DATABASE_URL=<Render PostgreSQL Internal URL>`
   - `JWT_SECRET_KEY=<generate 64-char random secret>`
   - `CORS_ORIGINS=https://<your-vercel-domain>.vercel.app`
   - Optional: `OPENAI_API_KEY` or `GEMINI_API_KEY` (leave unset for clearly labelled Deterministic Demo Mode)
3. `backend/Dockerfile` automatically runs `alembic -c backend/alembic.ini upgrade head` before starting `uvicorn backend.main:app --workers 1`.
4. Verify `GET https://<your-api-domain>/api/health` returns `{"status":"ok","product":"VYRO-X","ml_model_loaded":true}`.

### Frontend (Vercel)
1. Import the repository in Vercel with **Root Directory** set to `frontend`.
2. `frontend/vercel.json` is preconfigured for SPA route rewrites (`/* -> /index.html`).
3. Set Environment Variable:
   - `VITE_API_BASE_URL=https://<your-api-domain>`
4. Deploy and verify login, task creation, SSE streaming, ML predictions, and logout revocation.

---

## 3. Option B — Self-Hosted Docker Compose (PostgreSQL 16 + FastAPI + Nginx)
```bash
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export CORS_ORIGINS="https://your-domain.com"
docker compose up -d --build
```
Verify:
```bash
curl -fsS http://127.0.0.1:8080/api/health
```

---

## 4. PostgreSQL Backup & Recovery Procedure

### Logical Backup (`pg_dump`)
Never reset or drop a production database to resolve migration issues. Always take a timestamped backup before running schema migrations:
```bash
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl -f "vyrox_backup_$(date -u +%Y%m%d_%H%M%S).dump"
```

### Point-in-Time / Full Restore (`pg_restore`)
```bash
# Restore into a freshly provisioned recovery database first, verify integrity, then swap traffic
pg_restore --clean --if-exists --no-owner --no-acl -d "$RECOVERY_DATABASE_URL" vyrox_backup_YYYYMMDD_HHMMSS.dump
```

### Safe Alembic Migration Verification
```bash
alembic -c backend/alembic.ini current
alembic -c backend/alembic.ini upgrade head
```

---

## 5. Horizontal Scaling Note
Because `ExecutionManager`, `SSEBroker`, and `SlidingWindowRateLimiter` run in-process, keep `--workers 1` for single-node deployments. Before scaling beyond one backend instance, migrate those three components to a shared Redis backend.
