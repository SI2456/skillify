"""
Setup Google OAuth for Skillify.

Usage:
    set GOOGLE_CLIENT_ID=your-client-id
    set GOOGLE_CLIENT_SECRET=your-client-secret
    python manage.py setup_google_auth

Or setup manually in Django Admin.
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
import os


class Command(BaseCommand):
    help = 'Setup Google OAuth Social Application'

    def handle(self, *args, **kwargs):
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')

        # Step 1: Update Site
        site, _ = Site.objects.get_or_create(pk=1)
        site.domain = '127.0.0.1:8000'
        site.name = 'Skillify Local'
        site.save()
        self.stdout.write(f'  ✅ Site updated: {site.domain}')

        if not client_id or not client_secret:
            self.stdout.write(self.style.WARNING(
                '\n  ⚠️  GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set in environment.\n'
                '  You can set them up manually in Django Admin:\n'
                '  1. Go to http://127.0.0.1:8000/admin/\n'
                '  2. Social Applications → Add\n'
                '  3. Provider: Google\n'
                '  4. Name: Google\n'
                '  5. Client ID + Secret from Google Cloud Console\n'
                '  6. Sites: add 127.0.0.1:8000\n'
            ))
            return

        # Step 2: Create Social Application
        from allauth.socialaccount.models import SocialApp
        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        if not created:
            app.client_id = client_id
            app.secret = client_secret
            app.save()

        # Link to site
        app.sites.add(site)

        self.stdout.write(self.style.SUCCESS(
            f'  ✅ Google OAuth configured!\n'
            f'  Client ID: {client_id[:20]}...\n'
            f'  Callback URL: http://127.0.0.1:8000/accounts/google/login/callback/\n'
        ))
