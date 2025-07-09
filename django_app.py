#!/usr/bin/env python
"""
Django development server startup script
For production, use: python manage.py runserver or gunicorn
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Default to runserver for development
    if len(sys.argv) == 1:
        sys.argv.extend(['runserver', '0.0.0.0:8000'])
    
    execute_from_command_line(sys.argv)
