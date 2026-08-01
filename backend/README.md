# Patrol Pro Backend

The canonical Phase 1 ownership model, aggregate boundaries and compatibility
rules are defined in [`../docs/CANONICAL_DOMAIN_MODEL.md`](../docs/CANONICAL_DOMAIN_MODEL.md)
and [`../docs/PHASE1_API_COMPATIBILITY.md`](../docs/PHASE1_API_COMPATIBILITY.md).
Models without a complete workflow intentionally have no public API.

Patrol Pro is an MVP intended for controlled demonstration and pilot evaluation. It is not currently approved as the sole system for live security operations.

This FastAPI backend provides the current authenticated, organisation-scoped
API foundation. Production deployment mechanics exist, but operational
readiness remains subject to the documented pilot-readiness programme.

## Architecture

- **Framework**: FastAPI (modern, fast, async)
- **Database**: SQLAlchemy ORM with SQLite (local) / PostgreSQL (production)
- **Authentication**: JWT with HS256 signature
- **Security**: bcrypt password hashing, CORS, and process-local demo rate limiting
- **API Docs**: Auto-generated Swagger UI at `/api/docs`

## Quick Start

### 1. Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Initialization

```bash
# Run the initialization script to create tables and seed demo data
python3 init_db.py

# This will:
# ✓ Create all database tables
# ✓ Create demo user (officer1783163143325@patrol.pro / password123)
# ✓ Seed sample patrols and devices
```

### 3. Start the Backend

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Backend will be available at: **http://127.0.0.1:8000**

### 4. API Documentation

- **Swagger UI**: http://127.0.0.1:8000/api/docs
- **ReDoc**: http://127.0.0.1:8000/api/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/api/openapi.json

## API Endpoints

### Authentication

```bash
# Register new user
POST /api/v1/auth/register
Content-Type: application/json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "example-only-password-change-me"
}

# Login (returns JWT token)
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=example-only-password-change-me
```

### Patrols (Protected Routes - Require Bearer Token)

```bash
# Get all patrols (paginated)
GET /api/v1/patrols?skip=0&limit=100
Authorization: Bearer <token>

# Get specific patrol
GET /api/v1/patrols/{patrol_id}
Authorization: Bearer <token>

# Create patrol
POST /api/v1/patrols
Authorization: Bearer <token>
Content-Type: application/json
{
  "name": "Night Shift - Zone A",
  "description": "Perimeter patrol",
  "start_time": "2026-07-05T18:00:00",
  "end_time": "2026-07-05T22:00:00",
  "assigned_to": "Team Security Alpha"
}

# Update patrol
PUT /api/v1/patrols/{patrol_id}
Authorization: Bearer <token>
Content-Type: application/json
{ ... updated fields ... }

# Delete patrol
DELETE /api/v1/patrols/{patrol_id}
Authorization: Bearer <token>
```

### Devices, Customers, Alerts

Similar CRUD patterns available at:
- `/api/v1/devices` - Device management
- `/api/v1/customers` - Customer information
- `/api/v1/alerts` - Security alerts
- `/api/v1/users` - User management (admin only)

## Configuration

Configuration is managed via environment variables in `.env` file:

```env
# Database
DATABASE_URL=sqlite:///./patrol_pro.db
# Placeholder only: DATABASE_URL=postgresql://example_user:example_password@localhost:5432/patrol_pro

# Security (CHANGE THESE IN PRODUCTION)
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Server
HOST=127.0.0.1
PORT=8000
DEBUG=True

# CORS (adjust for production)
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

## Database Schema

### Users Table
```sql
id (PK) | email (unique) | full_name | hashed_password
```

### Patrols Table
```sql
id (PK) | name | description | start_time | end_time | assigned_to
```

### Devices Table
```sql
id (PK) | name | serial_number (unique) | status
```

### Customers Table
```sql
id (PK) | name | contact_email | phone | address
```

### Alerts Table
```sql
id (PK) | title | description | severity | status | reported_at |
patrol_id (FK) | device_id (FK) | customer_id (FK)
```

## Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py -v
```

## Deployment

### Docker

```bash
# Build image
docker build -t patrol-pro-backend .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://example_user:example_password@db:5432/patrol_pro \
  -e SECRET_KEY=your-production-secret-key \
  patrol-pro-backend
```

### Production Checklist

- [ ] Update `SECRET_KEY` to a strong random value (min 32 characters)
- [ ] Set `DEBUG=False` in environment
- [ ] Configure PostgreSQL instead of SQLite
- [ ] Set up proper CORS origins for frontend domain
- [ ] Enable HTTPS/TLS for API
- [ ] Configure database backups
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Set up SSL certificates
- [ ] Use environment-specific configuration files

### Recommended Production Stack

```
Frontend (React) → Load Balancer →
Backend (Uvicorn x4) → PostgreSQL
                    → Redis (caching/sessions)
                    → Nginx (reverse proxy)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./patrol_pro.db` | Database connection string |
| `SECRET_KEY` | `dev-key` | JWT signing secret (MUST change in production) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token expiration time |
| `HOST` | `127.0.0.1` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `True` | Debug mode |
| `RELOAD` | `True` | Auto-reload on file changes |
| `ALLOWED_ORIGINS` | Multiple localhost | CORS allowed origins |

## Troubleshooting

### Port Already in Use

```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Database Issues

```bash
# Reset database (WARNING: deletes all data)
rm patrol_pro.db
python3 init_db.py
```

### Authentication Errors

- Ensure `SECRET_KEY` is consistent across sessions
- Check that JWT token hasn't expired
- Verify CORS origins match frontend URL

## Performance Tips

1. **Database Indexes**: Add indexes on frequently queried columns
2. **Pagination**: Always use skip/limit for large result sets
3. **Caching**: Cache static lookup data (status enums, etc.)
4. **Database Connection**: Use connection pooling in production
5. **API Responses**: Implement response compression

## Security Considerations

1. **Passwords**: Hashed with bcrypt, never stored in plain text
2. **JWT**: Tokens expire after 60 minutes by default
3. **CORS**: Configure for specific origins only
4. **Input Validation**: All inputs validated with Pydantic
5. **SQL Injection**: Protected via SQLAlchemy ORM
6. **Rate Limiting**: Implement via Nginx/reverse proxy

## Contributing

Follow the existing code style:
- Use type hints for all functions
- Document public functions with docstrings
- Write tests for new features
- Keep functions under 50 lines when possible

## License

Proprietary - Patrol Pro
