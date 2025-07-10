#!/usr/bin/env python
"""
Cloud Run startup script with enhanced error handling and logging
"""
import os
import sys
import logging
import subprocess
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Check if database is accessible"""
    try:
        import django
        from django.core.management import execute_from_command_line
        from django.db import connection
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def run_migrations():
    """Run Django migrations with retry logic"""
    logger.info("Starting database migrations...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            import django
            from django.core.management import execute_from_command_line
            
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
            django.setup()
            
            # Run migrations
            execute_from_command_line(['manage.py', 'migrate', '--noinput'])
            logger.info("Database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error("All migration attempts failed")
                return False
    
    return False

def collect_static():
    """Collect static files"""
    try:
        logger.info("Collecting static files...")
        import django
        from django.core.management import execute_from_command_line
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        logger.info("Static files collected successfully")
        return True
    except Exception as e:
        logger.warning(f"Static file collection failed: {e}")
        return False

def start_server():
    """Start the web server"""
    logger.info("Starting web server...")
    
    port = os.environ.get('PORT', '8000')
    workers = os.environ.get('WEB_CONCURRENCY', '1')
    
    # Check if we're on Windows (development) or Linux (production)
    is_windows = os.name == 'nt'
    
    if is_windows:
        # Use Django development server on Windows
        logger.info("Windows detected, using Django development server")
        import django
        from django.core.management import execute_from_command_line
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        
        try:
            execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
            sys.exit(0)
    else:
        # Use gunicorn on Linux (Cloud Run)
        logger.info("Linux detected, using gunicorn")
        cmd = [
            'gunicorn',
            '--bind', f':{port}',
            '--workers', workers,
            '--timeout', '120',
            '--keep-alive', '2',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            'wsgi:application'
        ]
        
        logger.info(f"Starting server with command: {' '.join(cmd)}")
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Server failed to start: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
            sys.exit(0)

def main():
    """Main startup sequence"""
    logger.info("=== Django Cloud Run Startup ===")
    
    # Check if we're in production
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    if debug_mode:
        logger.info("Running in DEBUG mode")
    else:
        logger.info("Running in PRODUCTION mode")
    
    # Check database connection
    if not check_database_connection():
        logger.error("Cannot connect to database. Exiting.")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        logger.error("Migration failed. Exiting.")
        sys.exit(1)
    
    # Collect static files (optional, continues even if it fails)
    collect_static()
    
    # Start the server
    start_server()

if __name__ == '__main__':
    main()
