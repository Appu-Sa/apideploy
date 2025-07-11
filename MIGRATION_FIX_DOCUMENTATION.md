# Django Production Migration Fix for Cloud Run

## Problem
The Django API was failing in production with the error:
```
"relation \"api_user\" does not exist"
```

This indicated that database migrations were not being applied in the Cloud Run production environment.

## Root Cause
Cloud Run using buildpacks often ignores the `release` phase in the Procfile, so the command:
```
release: python manage.py migrate --noinput
```
Was not being executed, leaving the PostgreSQL database without the required tables.

## Solution Implemented

### 1. Created `cloud_run_startup.py`
A robust startup script that:
- **Checks database connectivity** before proceeding
- **Runs migrations automatically** with retry logic
- **Collects static files** (if needed)
- **Handles Windows/Linux differences** (Django dev server vs gunicorn)
- **Provides detailed logging** for debugging production issues

### 2. Updated Procfile
Changed from:
```
release: python manage.py migrate --noinput
web: gunicorn --bind :$PORT wsgi:application
```

To:
```
web: python cloud_run_startup.py
```

### 3. Enhanced Settings
- Added `STATIC_ROOT = BASE_DIR / 'staticfiles'` for static file collection
- Maintained secure database configuration for both local and production

### 4. Key Features of the Startup Script

#### Database Connection Check
```python
def check_database_connection():
    """Check if database is accessible"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
```

#### Migration with Retry Logic
```python
def run_migrations():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            execute_from_command_line(['manage.py', 'migrate', '--noinput'])
            return True
        except Exception as e:
            # Retry logic with 5-second delay
```

#### Environment Detection
```python
def start_server():
    is_windows = os.name == 'nt'
    if is_windows:
        # Use Django dev server for Windows
        execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])
    else:
        # Use gunicorn for Linux (Cloud Run)
        subprocess.run(['gunicorn', '--bind', f':{port}', 'wsgi:application'])
```

## Deployment Instructions

### For Cloud Run:
1. **Push to GitHub** (already done)
2. **Deploy to Cloud Run** - the startup script will automatically:
   - Connect to the PostgreSQL database
   - Run all pending migrations
   - Start the web server

### Environment Variables Required in Cloud Run:
```bash
DATABASE_URL=postgresql://flask_user:Test@12345@/flask_app_db?host=/cloudsql/august-strata-462911-t2:asia-south1:api-56
SECRET_KEY=your-secret-key-here
GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-credentials/credentials.json
```

### Mount Google Cloud Credentials:
In Cloud Run, mount the credentials JSON as a secret volume at:
```
/secrets/gcp-credentials/credentials.json
```

## Testing

### Local Testing:
```bash
python cloud_run_startup.py
```
- Uses SQLite database
- Uses Django development server
- Runs migrations automatically

### Production Testing:
After deployment, check Cloud Run logs to verify:
1. "Database connection successful"
2. "Database migrations completed successfully"
3. "Starting web server..."

## Expected Resolution
This fix ensures that the `api_user` table (and all other required tables) are created in the PostgreSQL database before the Django application starts serving requests, eliminating the "relation does not exist" error.

## Files Modified
- `cloud_run_startup.py` - New startup script
- `Procfile` - Updated to use startup script
- `settings.py` - Added STATIC_ROOT
- `.gitignore` - Improved cache file exclusion
- `api/migrations/` - Django migration files

The startup script approach is more reliable than relying on buildpack release phases and provides better error handling and logging for production deployments.
