web: python fix_railway_views.py && python fix_templates_and_aiohttp.py && python fix_multiple_fields.py && python fix_admin_query.py && python manage.py migrate && gunicorn core.wsgi:application --preload --max-requests 1000 --max-requests-jitter 100 --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:$PORT
bot: python run_bot.py
