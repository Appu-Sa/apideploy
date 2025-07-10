#!/bin/bash
# Startup script for Cloud Run - ensures migrations run before starting the server

echo "Starting Django application..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "Database migrations completed successfully."
else
    echo "Database migrations failed!"
    exit 1
fi

# Start the web server
echo "Starting web server..."
exec gunicorn --bind :$PORT wsgi:application
