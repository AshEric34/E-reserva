release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn ereserva.wsgi --bind 0.0.0.0:$PORT --workers 3