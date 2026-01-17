# Logistics Manager Backend

A scalable FastAPI backend application for logistics management.

## Tech Stack

- **Python**: 3.13.11
- **Framework**: FastAPI 0.115.*
- **Server**: Uvicorn 0.30.*
- **Validation**: Pydantic 2.8.*
- **ORM**: SQLAlchemy 2.0.*
- **Authentication**: python-jose 3.3.*
- **Password Hashing**: passlib 1.7.*

## Project Structure

```
backend/
├── app/
│   ├── main.py              # Application entry point
│   ├── core/                # Core configuration
│   │   ├── config.py        # Settings and configuration
│   │   └── security.py      # Security utilities
│   ├── api/                 # API routes
│   │   └── v1/              # API version 1
│   │       └── router.py    # API router
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── db/                  # Database configuration
│   │   └── session.py       # Database session
│   └── utils/               # Utility functions
├── tests/                   # Test suite
├── .env.example             # Environment variables example
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Setup

1. Create virtual environment:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r ../requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn backend.app.main:app --reload
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

## Development

This project follows FastAPI best practices with a clean, scalable architecture suitable for enterprise logistics management systems.
