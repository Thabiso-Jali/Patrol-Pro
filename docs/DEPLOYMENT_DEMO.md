# Patrol Pro Render demo deployment

This guide prepares a disposable demonstration environment. It does not
authorize creating services, changing DNS, or using real customer data.

## Architecture

- Render Static Site builds the React app from `frontend/`.
- Render Web Service builds the FastAPI Docker image from `backend/`.
- Render Postgres provides the demo database over Render's private network.
- Render provides HTTPS and `onrender.com` domains.

The browser loads the static site and calls the public HTTPS API. The API uses
Render's private PostgreSQL connection string.

## Database migrations

The repaired Alembic chain has one head, initializes an empty PostgreSQL 15
database, and matches the current SQLAlchemy metadata:

```bash
cd backend
alembic upgrade head
```

Never use `Base.metadata.create_all()` as a production migration substitute.
Render pre-deploy commands require a paid web service. For this single-instance
free demo only, the Blueprint's Docker command runs the idempotent migration
immediately before Uvicorn starts. Upgrade to a paid service and move the same
command to Render's pre-deploy setting before scaling beyond one instance.

## Local setup

Use Node.js/npm, Python 3.11 or newer, and optionally Docker Desktop.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic current
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm start
```

Local SQLite remains supported only with `APP_ENV=development`.

## Local PostgreSQL test

The Compose file starts PostgreSQL only with disposable local credentials:

```bash
docker compose -f docker-compose.demo.yml up -d
```

Use this `backend/.env` configuration:

```dotenv
APP_ENV=demo
DEBUG=false
DATABASE_URL=postgresql://patrol_pro:local-demo-only@localhost:5432/patrol_pro_demo
JWT_SECRET_KEY=replace-with-a-generated-secret-at-least-32-characters
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
```

Run `alembic upgrade head` before starting the API against this empty database.

## Secrets

Generate the JWT secret locally:

```bash
openssl rand -base64 48
```

Store it only in Render. Never place it in `render.yaml`, `.env.example`, React
variables, logs, screenshots, or tickets. Every `REACT_APP_*` value is public
because Create React App embeds it in browser assets.

## Render steps

1. Commit and push the reviewed changes only after approval.
2. Create a Render Blueprint from `render.yaml`.
3. Review the proposed free database, API, and static site.
4. Supply the prompted values below.
5. Keep automatic deployment disabled.
6. Create resources only after checking current cost and retention terms.
7. Confirm the API startup log shows `alembic upgrade head` succeeded before
   Uvicorn starts.
8. Verify the API `/health`, and then verify the static site.

The database blocks public network access. The static site has an SPA rewrite
and conservative headers. No custom domain is configured.

## Required Render values

Backend:

- `JWT_SECRET_KEY`: unique output from `openssl rand -base64 48`
- `CORS_ORIGINS`: exact static-site URL, such as
  `https://patrol-pro-demo-web.onrender.com`
- `FRONTEND_URL`: the same static-site URL
- `DATABASE_URL`: populated from Render Postgres by the Blueprint

Frontend:

- `REACT_APP_API_BASE_URL`: exact API origin, such as
  `https://patrol-pro-demo-api.onrender.com`

If Render changes a name for uniqueness, use the actual URL. Do not add trailing
slashes. Rebuild the static site whenever its API URL changes.

## Fake demo data

Never use real client, staff, medication, address, health, care, incident, or
security data. The seed command is explicit, idempotent for its fake records,
and never runs during application startup.

After the schema exists:

```bash
cd backend
APP_ENV=demo \
DEMO_ADMIN_EMAIL=demo-admin@example.invalid \
DEMO_ADMIN_PASSWORD='replace-with-a-temporary-random-password' \
python init_db.py
```

For development only, `--confirm-demo-data` explicitly permits the same
fake-data operation without `APP_ENV=demo`.

## Smoke tests

1. `GET https://<api-host>/health` returns HTTP 200 and small JSON.
2. `/api/docs` loads without internal error details.
3. The static site loads over HTTPS and direct-path refresh serves the SPA.
4. Registration or demo login succeeds.
5. An authenticated patrol request succeeds.
6. The browser shows no CORS, mixed-content, or localhost errors.
7. Logs contain no passwords, tokens, authorization headers, or database URLs.
8. The frontend build contains no localhost API URL or secrets.

## Logs and limitations

Use Render's service Logs view and filter by deploy time. `LOG_LEVEL` controls
backend verbosity; `DEBUG` must remain false in demo and production.

The in-memory rate limiter supports only a single demo instance. Access tokens
are kept in React memory, so refreshing signs the user out. A strict frontend
CSP was intentionally not added because it has not been tested.

## Rollback

1. Preserve logs and stop traffic-changing work.
2. Roll back the API or static site to its last known-good Render deploy.
3. Never downgrade the database automatically.
4. Restore schema/data into a separate database and verify it before changing
   the application's connection string.
5. Repeat the smoke tests.

Frontend and backend rollback independently, so keep their API contracts
compatible.

## Backup and data handling

SQLite must not be deployed. Demo data must be fake. Free demo PostgreSQL can be
disposable or expire as platform plans change; export anything needed before
expiry or deletion.

```bash
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > patrol-pro-demo.dump
```

Keep exports secure and delete them when no longer required. Production
customer data requires paid PostgreSQL with automated backups and verified
restore procedures. Never test a restore against the only database copy.

Before real customers, also add monitoring, alerting, restore drills, privacy
controls, retention policies, and a documented incident-response process.
