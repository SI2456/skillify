"""
Auto-reject reschedule requests that haven't been responded to within 30 minutes.
Run via cron every 5 minutes: python manage.py auto_reject_reschedules
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Booking, Session, Transaction, Notification


class Command(BaseCommand):
    help = 'Auto-reject reschedule requests older than 30 minutes'

    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=30)

        expired = Booking.objects.filter(
            reschedule_status='pending',
            reschedule_requested_at__lt=cutoff,
        )

        count = 0
        for booking in expired:
            booking.reschedule_status = 'auto_rejected'
            booking.status = 'cancelled'
            booking.save()

            # Refund credits
            wallet = booking.learner.wallet
            wallet.balance += booking.credits_paid
            wallet.save()
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                amount=booking.credits_paid,
                description=f'Refund: Reschedule auto-rejected (timeout) — {booking.session.title}',
                balance_after=wallet.balance,
            )

            Notification.create_notification(
                booking.learner, 'credits_refunded',
                f'{booking.credits_paid} credits refunded',
                f'Reschedule for "{booking.session.title}" expired (no response in 30 min). Credits returned.',
                '/wallet/'
            )

            Notification.create_notification(
                booking.session.tutor, 'dispute_opened',
                f'Reschedule expired: {booking.learner.get_full_name()}',
                f'{booking.learner.get_full_name()} did not respond to reschedule within 30 min. Booking cancelled.',
                '/my-sessions/'
            )

            count += 1

            # Check if session needs cancellation
            session = booking.session
            still_active = session.bookings.filter(
                status='confirmed'
            ).exclude(reschedule_status__in=['rejected', 'auto_rejected']).count()

            accepted = session.bookings.filter(reschedule_status='accepted').count()

            if still_active == 0 and accepted == 0:
                session.status = 'cancelled'
                session.save()
            elif accepted > 0:
                # Update session with new time from accepted bookings
                first_accepted = session.bookings.filter(reschedule_status='accepted').first()
                if first_accepted:
                    session.date = first_accepted.reschedule_new_date
                    session.start_time = first_accepted.reschedule_new_start
                    session.end_time = first_accepted.reschedule_new_end
                    session.save()

        self.stdout.write(f'  ✅ Auto-rejected {count} expired reschedule request(s)')
