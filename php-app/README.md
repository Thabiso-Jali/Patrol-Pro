# Patrol Pro PHP/MySQL App

Patrol Pro is an MVP intended for controlled demonstration and pilot evaluation. It is not currently approved as the sole system for live security operations.

This is a separate legacy demonstration implementation with a vanilla
HTML/CSS/JS interface. It is not the supported FastAPI/React SaaS path and must
not be connected to its production database.

## Local Setup

1. Create a local env file:

```bash
cp .env.example .env
```

2. Create the database:

```bash
mysql -u root -p < database/schema.sql
```

3. Run locally with PHP's built-in server:

```bash
php -S 127.0.0.1:8080 -t public public/router.php
```

4. Open `http://127.0.0.1:8080`.

Demo accounts use password `password`:

- `admin@patrolpro.local`
- `guard@patrolpro.local`
- `client@patrolpro.local`

## Structure

- `api/` REST dispatcher and request helpers
- `auth/` secure session and RBAC helpers
- `config/` PDO and app configuration
- `controllers/` request-level application actions
- `models/` PDO-backed data access with prepared statements
- `public/` responsive vanilla UI and incident uploads
- `database/schema.sql` MySQL schema and seed data

## Security Notes

- Passwords use PHP `password_hash(..., PASSWORD_BCRYPT)`.
- Database access uses PDO prepared statements.
- Session cookies are `HttpOnly` and `SameSite=Lax`.
- API endpoints enforce role access with `require_auth`.
- Incident image uploads validate MIME type and size.
- Audit log rows are written for sensitive actions.

## Production Deployment

Start with:

```bash
cp .env.production.example .env
```

Then edit `.env` with your real domain, database user, and database password.

Use the full deployment checklist and web server templates in:

- `deploy/DEPLOYMENT.md`
- `deploy/nginx-patrol-pro.conf`
- `deploy/apache-patrol-pro.conf`

Production web root must be `php-app/public`, not the project root.
