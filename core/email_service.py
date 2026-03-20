"""
Email Notification Service for Skillify.
Uses HTML templates with branding for all emails.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

SITE_URL = 'http://127.0.0.1:8000'


def _send_html_email(subject, template, context, to_email):
    """Send an HTML email using a template. Falls back to plain text."""
    context['site_url'] = SITE_URL
    try:
        html_content = render_to_string(template, context)
        # Strip HTML for plain text fallback
        import re
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f'Email sent to {to_email}: {subject}')
        return True
    except Exception as e:
        logger.error(f'Failed to send email to {to_email}: {e}')
        return False


def notify_tutor_new_booking(booking):
    """Send branded HTML email to tutor when a learner books their session."""
    session = booking.session
    return _send_html_email(
        subject=f'🎉 New Booking: "{session.title}" - Skillify',
        template='emails/booking_tutor.html',
        context={
            'tutor_name': session.tutor.first_name,
            'session_title': session.title,
            'session_date': session.date.strftime('%B %d, %Y'),
            'session_time': f'{session.start_time.strftime("%I:%M %p")} - {session.end_time.strftime("%I:%M %p")}',
            'learner_name': booking.learner.get_full_name(),
            'learner_email': booking.learner.email,
            'credits': session.credits_required,
            'skill_name': session.skill.name,
        },
        to_email=session.tutor.email,
    )


def notify_learners_booking_confirmation(booking):
    """Send branded HTML booking confirmation to learner."""
    session = booking.session
    return _send_html_email(
        subject=f'✅ Booking Confirmed: "{session.title}" - Skillify',
        template='emails/booking_learner.html',
        context={
            'learner_name': booking.learner.first_name,
            'session_title': session.title,
            'tutor_name': session.tutor.get_full_name(),
            'session_date': session.date.strftime('%B %d, %Y'),
            'session_time': f'{session.start_time.strftime("%I:%M %p")} - {session.end_time.strftime("%I:%M %p")}',
            'credits': booking.credits_paid,
            'zoom_url': session.zoom_join_url,
            'zoom_id': session.zoom_meeting_id,
            'zoom_pass': session.zoom_password,
        },
        to_email=booking.learner.email,
    )


def notify_tutor_session_reminder(session):
    """Send reminder email to tutor 15 min before session."""
    booking_count = session.bookings.filter(status='confirmed').count()
    if booking_count == 0:
        return False

    return _send_html_email(
        subject=f'⏰ Reminder: "{session.title}" starts soon! - Skillify',
        template='emails/session_reminder.html',
        context={
            'tutor_name': session.tutor.first_name,
            'session_title': session.title,
            'session_time': f'{session.start_time.strftime("%I:%M %p")} - {session.end_time.strftime("%I:%M %p")}',
            'learner_count': booking_count,
            'zoom_url': session.zoom_start_url,
        },
        to_email=session.tutor.email,
    )


def notify_learners_session_starting(session):
    """Send Zoom link email to all learners when tutor starts session."""
    bookings = session.bookings.filter(status='confirmed').select_related('learner')
    sent = 0

    for booking in bookings:
        success = _send_html_email(
            subject=f'🎬 Session Starting Now: "{session.title}" - Skillify',
            template='emails/session_starting.html',
            context={
                'learner_name': booking.learner.first_name,
                'session_title': session.title,
                'tutor_name': session.tutor.get_full_name(),
                'session_time': f'{session.start_time.strftime("%I:%M %p")} - {session.end_time.strftime("%I:%M %p")}',
                'zoom_url': session.zoom_join_url,
                'zoom_id': session.zoom_meeting_id,
                'zoom_pass': session.zoom_password,
            },
            to_email=booking.learner.email,
        )
        if success:
            sent += 1

    return sent


def send_otp_email(email, otp_code, purpose='verify your account'):
    """Send OTP with branded HTML template."""
    return _send_html_email(
        subject=f'🔐 Your Skillify Verification Code: {otp_code}',
        template='emails/otp.html',
        context={
            'otp_code': otp_code,
            'purpose': purpose,
        },
        to_email=email,
    )
