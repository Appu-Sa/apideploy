release: python manage.py migrate --noinput
web: gunicorn --bind :$PORT wsgi:application
