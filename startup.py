#!/usr/bin/env python
"""
Production startup script for Cloud Run
Runs migrations and starts the Django application
"""
import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def run_migrations():
    """Run Django migrations"""
    print("Running database migrations...")
    try:
        # Set up Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        
        # Run migrations
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        print("Database migrations completed successfully.")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

def start_server():
    """Start the gunicorn server"""
    print("Starting web server...")
    port = os.environ.get('PORT', '8000')
    cmd = ['gunicorn', '--bind', f':{port}', 'wsgi:application']
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Run migrations first
    if not run_migrations():
        print("Exiting due to migration failure")
        sys.exit(1)
    
    # Start the server
    start_server()
