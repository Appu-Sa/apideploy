# Django API with Google Cloud Integration

A clean, production-ready Django REST API with Google Cloud Storage and Video Intelligence integration.

## 📁 Project Structure

```
├── 🐍 Django Core
│   ├── settings.py         # Django configuration
│   ├── urls.py             # Main URL routing
│   ├── wsgi.py             # WSGI application
│   ├── manage.py           # Django management
│   ├── django_app.py       # Quick startup script
│   └── __init__.py         # Package initialization
│
├── 📱 API Application
│   └── api/
│       ├── models.py       # Database models
│       ├── views.py        # API endpoints
│       ├── serializers.py  # Data serialization
│       ├── utils.py        # GCS & Video Intelligence
│       ├── urls.py         # API routing
│       ├── admin.py        # Django admin
│       ├── apps.py         # App configuration
│       └── __init__.py     # Package initialization
│
├── 🚀 Deployment
│   ├── requirements.txt    # Dependencies
│   ├── Procfile           # Cloud Run
│   ├── app.yaml           # App Engine
│   ├── runtime.txt        # Python version
│   ├── .dockerignore      # Docker ignore
│   └── .gcloudignore      # GCloud ignore
│
├── ⚙️ Configuration
│   ├── .env               # Environment variables
│   ├── .gitignore         # Git ignore
│   └── august-strata-*    # GCP credentials
│
└── 🔧 Development
    ├── venv/              # Virtual environment
    └── .git/              # Git repository
```

## 🚀 Quick Start

### 1. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Run Django Server
```powershell
# Development (SQLite)
$env:DATABASE_URL=""
python manage.py runserver 0.0.0.0:8000

# Or use the startup script
python django_app.py
```

### 3. Access API
- API Base URL: `http://localhost:8000/api/`
- Health Check: `http://localhost:8000/api/health/`
- Django Admin: `http://localhost:8000/admin/`

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/health/` | GET | Health check |
| `/api/users/` | GET/POST | User management |
| `/api/upload-image/` | POST | Image upload to GCS |
| `/api/upload-video/` | POST | Video upload to GCS |
| `/api/analyze-video/` | POST | Video Intelligence analysis |
| `/api/signed-upload-url/` | POST | Generate signed URLs |

## 🗄️ Database Setup

### Development (SQLite - Default)
```powershell
python manage.py migrate
```

### Production (PostgreSQL)
1. Set `DATABASE_URL` in `.env`
2. Install PostgreSQL dependency: `pip install psycopg2-binary`
3. Run migrations: `python manage.py migrate`

## 🚀 Deployment

### Cloud Run
```bash
gcloud run deploy --source .
```

### App Engine
```bash
gcloud app deploy
```

## 🔧 Django Commands

```powershell
# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Check configuration
python manage.py check

# Collect static files (production)
python manage.py collectstatic
```

## 📁 Project Structure

```
├── api/                     # Django app
│   ├── models.py           # Database models
│   ├── views.py            # API endpoints
│   ├── serializers.py      # Data serialization
│   ├── utils.py            # GCS & Video Intelligence
│   └── urls.py             # API routing
├── settings.py             # Django configuration
├── urls.py                 # Main URL routing
├── wsgi.py                 # WSGI application
├── manage.py               # Django management
├── django_app.py           # Quick startup script
├── requirements.txt        # Dependencies
├── Procfile                # Cloud Run deployment
├── app.yaml                # App Engine deployment
└── .env                    # Environment variables
```

## 🔑 Environment Variables

Create/update `.env` file:
```
# For SQLite development (comment out DATABASE_URL)
# DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Google Cloud
GCS_BUCKET=your-storage-bucket
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Django
SECRET_KEY=your-secret-key
DEBUG=True
```

## 🛠️ Dependencies

- Django 4.2.7
- Django REST Framework
- Google Cloud Storage
- Google Cloud Video Intelligence
- CORS Headers
- Database URL parsing
