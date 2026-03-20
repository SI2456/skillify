"""
Send session reminder emails to tutors whose sessions start within 15 minutes.

Usage:
    python manage.py send_reminders

Setup (cron job - run every 15 minutes):
    */15 * * * * cd /path/to/skillify_project && python manage.py send_reminders

On Windows (Task Scheduler):
    Run every 15 minutes: python manage.py send_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Session


class Command(BaseCommand):
    help = 'Send reminder emails to tutors whose sessions start within 15 minutes'

    def handle(self, *args, **kwargs):
        from core.email_service import notify_tutor_session_reminder

        now = timezone.localtime()
        today = now.date()
        current_time = now.time()

        # Find sessions starting within next 15 minutes
        reminder_window = (now + timedelta(minutes=15)).time()

        upcoming_sessions = Session.objects.filter(
            date=today,
            status='upcoming',
            start_time__gte=current_time,
            start_time__lte=reminder_window,
        ).select_related('tutor', 'skill')

        if not upcoming_sessions.exists():
            self.stdout.write('No sessions starting in the next 15 minutes.')
            return

        sent_count = 0
        for session in upcoming_sessions:
            # Check if session has bookings
            if session.bookings.filter(status='confirmed').exists():
                success = notify_tutor_session_reminder(session)
                if success:
                    sent_count += 1
                    self.stdout.write(
                        f'  ✅ Reminder sent to {session.tutor.email} for "{session.title}" '
                        f'at {session.start_time.strftime("%I:%M %p")}'
                    )

        self.stdout.write(self.style.SUCCESS(f'Done! {sent_count} reminders sent.'))
