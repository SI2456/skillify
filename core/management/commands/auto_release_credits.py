"""
Auto-release credits 30 minutes after tutor confirms if learner hasn't responded.

Usage: python manage.py auto_release_credits
Cron:  */10 * * * * cd /path/to/project && python manage.py auto_release_credits
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Booking


class Command(BaseCommand):
    help = 'Auto-release credits after 30 min if learner has not confirmed'

    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=30)

        pending = Booking.objects.filter(
            tutor_confirmed=True,
            learner_confirmed=False,
            is_disputed=False,
            status='tutor_completed',
            tutor_confirmed_at__lte=cutoff,
        )

        released = 0
        for booking in pending:
            booking.learner_confirmed = True
            booking.learner_confirmed_at = timezone.now()
            booking.check_dual_completion()

            session = booking.session
            still_pending = session.bookings.filter(
                status__in=['confirmed', 'tutor_completed', 'learner_completed']
            ).count()
            if still_pending == 0:
                session.status = 'completed'
                session.save()

            released += 1
            self.stdout.write(
                f'  ✅ Auto-released: {session.title} → '
                f'{booking.credits_paid} credits to {session.tutor.email}'
            )

        self.stdout.write(self.style.SUCCESS(f'\nDone! {released} bookings auto-released.'))
