# AI Bot Platform

Telegram AI platform with:
- Telegram bot on `aiogram`
- Backend API on `FastAPI`
- `PostgreSQL` + `SQLAlchemy`
- `Redis` + `Celery`
- Telegram Mini App on `Next.js`
- Plans, orders, payments, balance, and credit history
- RU / UZ localization

## Architecture

- `backend/`: REST API, DB init, plans, orders, payments, balances
- `bot/`: Telegram bot flow, language selection, balance, plan purchase
- `miniapp/`: cabinet, wallet, plans, checkout, partnership pages
- `worker/`: Celery entrypoint and task placeholders
- `shared/`: enums and shared helpers
- `tests/`: API smoke tests with `unittest`
- `scripts/railway/`: shared start/build scripts for Railway services

## Implemented MVP flows

- Create or sync Telegram user from bot and mini app
- Auto-seed default plans on backend startup
- Create order for a selected plan
- Create payment for the order
- Confirm payment and credit the wallet
- Accept provider callbacks for `cards`, `payme`, and `click`
- Run AI generation jobs in mock-ready mode for `Nano Banana`, `Kling`, and `Veo`
- View balance and transaction history
- View recent orders in the mini app dashboard

## Webhook endpoints

- `POST /api/webhooks/cards/`
- `POST /api/webhooks/payme/`
- `POST /api/webhooks/click/`

Notes:
- If provider secret keys are configured, webhook requests must pass the matching secret.
- Supported auth headers are provider-specific secret headers or `Authorization: Bearer <secret>`.
- Incoming webhook payloads are logged into `webhook_logs` with sensitive headers redacted.

## Generation endpoints

- `POST /api/jobs/`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/telegram/{telegram_user_id}`

Generation notes:
- `AI_MOCK_MODE=true` lets the pipeline work without real provider keys.
- `GENERATION_PROCESS_NOW=true` processes jobs immediately inside the API flow for fast local testing.
- Set `GENERATION_PROCESS_NOW=false` to queue jobs through Celery.
- `CELERY_TASK_ALWAYS_EAGER=true` is useful for local/tests when you want queue semantics without a running worker.
- `GENERATION_POLL_INTERVAL_SECONDS` and `GENERATION_POLL_ATTEMPTS` control Kie polling in worker mode.
- `GENERATION_CALLBACK_BASE_URL` is optional and can be added later when you introduce provider callbacks for AI jobs.
- Later you can switch to real providers by setting AI keys and using worker-based execution.

## Local setup

1. Copy `.env.example` to `.env` and fill in your real values.
2. Start infrastructure:

```bash
docker compose up -d
```

3. Install Python dependencies:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

4. Run backend:

```bash
./.venv/bin/uvicorn backend.main:app --reload
```

5. Run bot:

```bash
./.venv/bin/python bot/main.py
```

6. Run worker:

```bash
./.venv/bin/celery -A worker.main.celery_app worker -l info
```

7. Run mini app:

```bash
cd miniapp
npm install
npm run dev
```

## Railway deploy

This repository is a shared monorepo, so the easiest Railway setup is four separate
services that all point to the same GitHub repository root:

- `backend`
- `worker`
- `bot`
- `miniapp`

Railway docs I used for this setup:
- https://docs.railway.com/guides/monorepo
- https://docs.railway.com/config-as-code
- https://docs.railway.com/reference/config-as-code
- https://docs.railway.com/guides/start-command

Recommended Railway service configuration:

1. Create a Railway project connected to your GitHub repository.
2. Add `Postgres` and `Redis` to the Railway project.
3. Create four services from the same repository.
4. For each service, set the Config-as-Code path in Railway Settings:

- backend: `/backend/railway.json`
- worker: `/worker/railway.json`
- bot: `/bot/railway.json`
- miniapp: `/miniapp/railway.json`

Required shared variables for backend / worker / bot:

- `POSTGRES_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `DEFAULT_LANGUAGE`
- `AI_MOCK_MODE=false`
- `GENERATION_PROCESS_NOW=false`
- `CELERY_TASK_ALWAYS_EAGER=false`
- `KIE_API_KEY`
- `KIE_BASE_URL=https://api.kie.ai`

Additional variables:

- backend:
  `MINIAPP_URL=https://<your-miniapp-domain>`
- bot:
  `BOT_TOKEN=<telegram bot token>`
  `MINIAPP_URL=https://<your-miniapp-domain>`
- miniapp:
  `BACKEND_INTERNAL_URL=https://<your-backend-domain>`
  `MINIAPP_URL=https://<your-miniapp-domain>`

Notes:

- `miniapp` proxies `/api/*` through `BACKEND_INTERNAL_URL` or `NEXT_PUBLIC_BACKEND_URL`, so you no longer need a localhost-only rewrite.
- The bot should be started as `python -m bot.main`, not `python bot/main.py`.
- The backend healthcheck path is `/health`.
- `railway.json` is intentionally service-specific to avoid one shared `startCommand` breaking worker or bot deployments in a monorepo.

## Verification

Python tests:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Mini app lint:

```bash
cd miniapp
npm run lint
```

Mini app production build:

```bash
cd miniapp
npm run build
```
