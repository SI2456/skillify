#!/usr/bin/env bash
# Render Build Script
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_future_sessions --start-date 2026-05-09 --days 30 --slots-per-day 2
python manage.py seed_mock_reviews --end-date 2026-05-08 --sessions-per-tutor 3 --reviews-per-session 2

# Create superuser if not exists
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@skillify.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
"

# Setup site for allauth
python manage.py shell -c "
from django.contrib.sites.models import Site
import os
domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')
site, _ = Site.objects.get_or_create(pk=1)
site.domain = domain
site.name = 'Skillify'
site.save()
print(f'Site updated: {domain}')
"
