# OPIK Backend API

A production-ready FastAPI application with JWT authentication, SQLite database, and comprehensive user management.

## Features

- ✅ **FastAPI Framework** - Modern, fast, high-performance web framework
- ✅ **JWT Authentication** - Secure token-based authentication with access and refresh tokens
- ✅ **User Management** - Complete CRUD operations for users
- ✅ **SQLite Database** - Lightweight database with SQLAlchemy ORM
- ✅ **Password Hashing** - Secure password storage using bcrypt
- ✅ **Pydantic Validation** - Request/response validation and serialization
- ✅ **CORS Support** - Cross-Origin Resource Sharing configured
- ✅ **Production Structure** - Clean, scalable folder architecture
- ✅ **API Documentation** - Auto-generated Swagger UI and ReDoc

## Project Structure

```
opik_Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # Database configuration
│   ├── dependencies.py         # Auth dependencies
│   ├── api/
│   │   └── v1/
│   │       ├── api.py          # API router
│   │       └── endpoints/
│   │           ├── auth.py     # Authentication endpoints
│   │           └── users.py    # User management endpoints
│   ├── core/
│   │   ├── config.py           # Application settings
│   │   └── security.py         # Security utilities (JWT, password)
│   ├── models/
│   │   └── user.py             # SQLAlchemy models
│   ├── schemas/
│   │   ├── user.py             # Pydantic schemas
│   │   └── token.py            # Token schemas
│   └── crud/
│       └── user.py             # Database operations
├── .env.example                # Environment variables template
├── .gitignore
├── requirements.txt            # Python dependencies
└── README.md
```

## Installation

### 1. Clone the repository

```bash
cd c:\xampp\htdocs\opik_Backend
```

### 2. Create virtual environment

```bash
python -m venv venv
```

### 3. Activate virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` file and update the `SECRET_KEY`:
```
SECRET_KEY=your-generated-secret-key-here
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Documentation**: http://localhost:8000/api/docs
- **ReDoc Documentation**: http://localhost:8000/api/redoc

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/signup` | Register new user | No |
| POST | `/api/v1/auth/login` | Login user | No |
| POST | `/api/v1/auth/logout` | Logout user | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |

### Users

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/users/me` | Get current user info | Yes |
| PUT | `/api/v1/users/me` | Update current user | Yes |
| GET | `/api/v1/users/` | Get all users | Yes (Superuser) |
| GET | `/api/v1/users/{user_id}` | Get user by ID | Yes (Superuser) |
| DELETE | `/api/v1/users/{user_id}` | Delete user | Yes (Superuser) |

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |

## Usage Examples

### 1. Sign Up

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 3. Get Current User Info

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Refresh Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## Security Features

- **Password Hashing**: Passwords are hashed using bcrypt
- **JWT Tokens**: Stateless authentication with access and refresh tokens
- **Token Expiration**: Access tokens expire in 30 minutes, refresh tokens in 7 days
- **CORS Protection**: Configurable CORS origins
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | OPIK Backend API |
| `SECRET_KEY` | JWT secret key | (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiration | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration | 7 |
| `DATABASE_URL` | Database connection string | sqlite:///./opik.db |
| `DEBUG` | Debug mode | False |

## Database Schema

### Users Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| email | String | Unique email address |
| username | String | Unique username |
| hashed_password | String | Bcrypt hashed password |
| full_name | String | User's full name (optional) |
| is_active | Boolean | Account active status |
| is_superuser | Boolean | Superuser privileges |
| created_at | DateTime | Account creation timestamp |
| updated_at | DateTime | Last update timestamp |

## Production Deployment

### 1. Update environment variables

Set production values in `.env`:
- Generate a strong `SECRET_KEY`
- Set `DEBUG=False`
- Configure specific CORS origins
- Use production database if needed

### 2. Use production server

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 3. Use reverse proxy (Nginx)

Configure Nginx to proxy requests to Uvicorn.

### 4. Enable HTTPS

Use SSL certificates (Let's Encrypt) for secure communication.

## Development

### Adding New Endpoints

1. Create new endpoint file in `app/api/v1/endpoints/`
2. Define routes using FastAPI router
3. Register router in `app/api/v1/api.py`

### Adding New Models

1. Create model in `app/models/`
2. Create schema in `app/schemas/`
3. Create CRUD operations in `app/crud/`
4. Update database initialization

## License

MIT License

## Author

OPIK Development Team

## Support

For issues and questions, please open an issue on GitHub.
