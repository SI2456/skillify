"""
Skillify Custom Admin Panel Views
All AJAX-powered API endpoints for the admin dashboard.
"""
import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Skill, UserProfile, Session, Booking, Review, Wallet, Transaction,
    Notification, TutorAvailability, SessionMaterial, Conversation, Message, Payment,
    SessionReport
)


def is_admin(user):
    return user.is_staff or user.is_superuser


def admin_required(view_func):
    """Decorator: login + admin check."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        if not is_admin(request.user):
            return JsonResponse({'error': 'Admin access required'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== DASHBOARD PAGE ====================

@login_required
@user_passes_test(is_admin)
def admin_panel_view(request):
    """Render the custom admin panel page."""
    return render(request, 'core/admin_panel.html')


# ==================== STATS API ====================

@admin_required
def admin_api_stats(request):
    """Dashboard statistics."""
    today = timezone.now().date()
    thirty_days = today - timedelta(days=30)
    seven_days = today - timedelta(days=7)

    total_users = User.objects.count()
    total_tutors = UserProfile.objects.filter(role='tutor').count()
    total_learners = UserProfile.objects.filter(role='learner').count()
    total_skills = Skill.objects.count()
    total_sessions = Session.objects.count()
    upcoming_sessions = Session.objects.filter(status='upcoming').count()
    completed_sessions = Session.objects.filter(status='completed').count()
    total_bookings = Booking.objects.count()
    total_reviews = Review.objects.count()
    open_disputes = Booking.objects.filter(is_disputed=True, dispute_resolved=False).count()
    total_credits_circulation = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
    total_messages = Message.objects.count()

    # Revenue stats
    paid_payments = Payment.objects.filter(status='paid')
    total_revenue = sum(p.amount_inr for p in paid_payments) // 100
    total_credits_purchased = sum(p.credits for p in paid_payments)

    # New users this week / month
    new_users_week = User.objects.filter(date_joined__date__gte=seven_days).count()
    new_users_month = User.objects.filter(date_joined__date__gte=thirty_days).count()

    # Recent activity
    recent_bookings = Booking.objects.select_related(
        'learner', 'session', 'session__tutor'
    ).order_by('-booked_at')[:10]

    recent_reviews = Review.objects.select_related(
        'reviewer', 'tutor', 'session'
    ).order_by('-created_at')[:10]

    recent_activity = []
    for b in recent_bookings:
        recent_activity.append({
            'type': 'booking',
            'text': f'{b.learner.get_full_name()} booked "{b.session.title}" with {b.session.tutor.get_full_name()}',
            'time': b.booked_at.strftime('%b %d, %I:%M %p'),
            'status': b.status,
        })
    for r in recent_reviews:
        recent_activity.append({
            'type': 'review',
            'text': f'{r.reviewer.get_full_name()} rated {r.tutor.get_full_name()} {r.rating}⭐',
            'time': r.created_at.strftime('%b %d, %I:%M %p'),
        })
    recent_activity.sort(key=lambda x: x['time'], reverse=True)

    return JsonResponse({
        'total_users': total_users,
        'total_tutors': total_tutors,
        'total_learners': total_learners,
        'total_skills': total_skills,
        'total_sessions': total_sessions,
        'upcoming_sessions': upcoming_sessions,
        'completed_sessions': completed_sessions,
        'total_bookings': total_bookings,
        'total_reviews': total_reviews,
        'open_disputes': open_disputes,
        'total_credits': total_credits_circulation,
        'total_messages': total_messages,
        'total_revenue': total_revenue,
        'total_credits_purchased': total_credits_purchased,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        'recent_activity': recent_activity[:15],
    })


# ==================== USER MANAGEMENT ====================

@admin_required
def admin_api_users(request):
    """List/search users."""
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    page = int(request.GET.get('page', 1))
    per_page = 20

    users = User.objects.select_related('profile', 'wallet').all()
    if search:
        users = users.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(email__icontains=search) | Q(username__icontains=search)
        )
    if role:
        users = users.filter(profile__role=role)

    users = users.order_by('-date_joined')
    total = users.count()
    users = users[(page-1)*per_page:page*per_page]

    data = []
    for u in users:
        p = u.profile
        data.append({
            'id': u.pk, 'name': u.get_full_name() or u.username,
            'email': u.email, 'role': p.role, 'trust_score': p.trust_score,
            'is_verified': p.is_verified, 'is_active': u.is_active,
            'is_staff': u.is_staff, 'balance': u.wallet.balance,
            'joined': u.date_joined.strftime('%b %d, %Y'),
            'avatar': p.avatar_url(),
            'bookings': Booking.objects.filter(learner=u).count(),
            'sessions_taught': Session.objects.filter(tutor=u, status='completed').count(),
        })

    return JsonResponse({'users': data, 'total': total, 'page': page, 'per_page': per_page})


@csrf_exempt
@admin_required
def admin_api_user_action(request, user_id):
    """Perform action on a user: suspend, activate, delete, make_admin, edit."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = get_object_or_404(User, pk=user_id)
    data = json.loads(request.body)
    action = data.get('action', '')

    if action == 'suspend':
        user.is_active = False
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.get_full_name()} suspended.'})

    elif action == 'activate':
        user.is_active = True
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.get_full_name()} activated.'})

    elif action == 'delete':
        name = user.get_full_name()
        user.delete()
        return JsonResponse({'success': True, 'message': f'{name} deleted.'})

    elif action == 'make_admin':
        user.is_staff = True
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.get_full_name()} is now admin.'})

    elif action == 'remove_admin':
        user.is_staff = False
        user.save()
        return JsonResponse({'success': True, 'message': f'{user.get_full_name()} admin removed.'})

    elif action == 'edit':
        if data.get('trust_score') is not None:
            user.profile.trust_score = float(data['trust_score'])
            user.profile.save()
        if data.get('role'):
            user.profile.role = data['role']
            user.profile.save()
        if data.get('balance') is not None:
            user.wallet.balance = int(data['balance'])
            user.wallet.save()
        return JsonResponse({'success': True, 'message': 'User updated.'})

    return JsonResponse({'error': 'Unknown action'}, status=400)


# ==================== SKILL MANAGEMENT ====================

@admin_required
def admin_api_skills(request):
    """List skills with stats."""
    skills = Skill.objects.annotate(
        session_count=Count('sessions'),
        tutor_count=Count('users', distinct=True),
        booking_count=Count('sessions__bookings'),
    ).order_by('-booking_count')

    data = []
    for s in skills:
        data.append({
            'id': s.pk, 'name': s.name, 'icon': s.icon,
            'sessions': s.session_count, 'tutors': s.tutor_count,
            'bookings': s.booking_count,
        })

    return JsonResponse({'skills': data})


@csrf_exempt
@admin_required
def admin_api_skill_action(request):
    """Add, edit, delete skills."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    data = json.loads(request.body)
    action = data.get('action', '')

    if action == 'add':
        name = data.get('name', '').strip()
        icon = data.get('icon', 'bi-lightbulb')
        if not name:
            return JsonResponse({'error': 'Name required'}, status=400)
        if Skill.objects.filter(name__iexact=name).exists():
            return JsonResponse({'error': 'Skill already exists'}, status=400)
        skill = Skill.objects.create(name=name, icon=icon)
        return JsonResponse({'success': True, 'message': f'Skill "{name}" created.', 'id': skill.pk})

    elif action == 'edit':
        skill = get_object_or_404(Skill, pk=data.get('id'))
        skill.name = data.get('name', skill.name)
        skill.icon = data.get('icon', skill.icon)
        skill.save()
        return JsonResponse({'success': True, 'message': f'Skill updated.'})

    elif action == 'delete':
        skill = get_object_or_404(Skill, pk=data.get('id'))
        name = skill.name
        skill.delete()
        return JsonResponse({'success': True, 'message': f'Skill "{name}" deleted.'})

    return JsonResponse({'error': 'Unknown action'}, status=400)


# ==================== SESSION MANAGEMENT ====================

@admin_required
def admin_api_sessions(request):
    """List sessions with filters."""
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')

    sessions = Session.objects.select_related('tutor', 'skill').all()
    if status:
        sessions = sessions.filter(status=status)
    if search:
        sessions = sessions.filter(
            Q(title__icontains=search) | Q(tutor__first_name__icontains=search) |
            Q(skill__name__icontains=search)
        )

    sessions = sessions.order_by('-date')[:50]

    data = []
    for s in sessions:
        data.append({
            'id': s.pk, 'title': s.title, 'tutor': s.tutor.get_full_name(),
            'skill': s.skill.name, 'level': s.get_level_display(),
            'date': s.date.strftime('%b %d, %Y'),
            'time': f'{s.start_time.strftime("%H:%M")}-{s.end_time.strftime("%H:%M")}',
            'credits': s.credits_required, 'status': s.status,
            'bookings': s.bookings.count(), 'has_zoom': bool(s.zoom_join_url),
            'materials': s.materials.count(),
        })

    return JsonResponse({'sessions': data})


# ==================== DISPUTE MANAGEMENT ====================

@admin_required
def admin_api_disputes(request):
    """List open disputes."""
    disputes = Booking.objects.filter(is_disputed=True).select_related(
        'learner', 'session', 'session__tutor', 'session__skill'
    ).order_by('-dispute_created_at')

    data = []
    for b in disputes:
        data.append({
            'id': b.pk, 'learner': b.learner.get_full_name(),
            'tutor': b.session.tutor.get_full_name(),
            'session': b.session.title, 'skill': b.session.skill.name,
            'credits': b.credits_paid, 'reason': b.dispute_reason,
            'created': b.dispute_created_at.strftime('%b %d, %I:%M %p') if b.dispute_created_at else '',
            'resolved': b.dispute_resolved, 'status': b.status,
        })

    return JsonResponse({'disputes': data})


@csrf_exempt
@admin_required
def admin_api_dispute_action(request, booking_id):
    """Resolve a dispute."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    booking = get_object_or_404(Booking, pk=booking_id, is_disputed=True)
    data = json.loads(request.body)
    action = data.get('action', '')

    if action == 'release':
        booking.dispute_resolved = True
        booking.is_disputed = False
        booking.tutor_confirmed = True
        booking.learner_confirmed = True
        booking.check_dual_completion()
        booking.session.status = 'completed'
        booking.session.save()
        Notification.create_notification(
            booking.session.tutor, 'dispute_resolved',
            'Dispute resolved in your favor',
            f'Credits for "{booking.session.title}" have been released.',
            '/my-sessions/'
        )
        return JsonResponse({'success': True, 'message': 'Credits released to tutor.'})

    elif action == 'refund':
        booking.dispute_resolved = True
        booking.status = 'cancelled'
        booking.save()
        wallet = booking.learner.wallet
        wallet.balance += booking.credits_paid
        wallet.save()
        Transaction.objects.create(
            wallet=wallet, transaction_type='credit',
            amount=booking.credits_paid,
            description=f'Refund: Dispute for {booking.session.title}',
            balance_after=wallet.balance,
        )
        Notification.create_notification(
            booking.learner, 'credits_refunded',
            'Dispute resolved — credits refunded',
            f'{booking.credits_paid} credits refunded for "{booking.session.title}".',
            '/wallet/'
        )
        return JsonResponse({'success': True, 'message': 'Credits refunded to learner.'})

    return JsonResponse({'error': 'Unknown action'}, status=400)


# ==================== REVIEW MANAGEMENT ====================

@admin_required
def admin_api_reviews(request):
    """List reviews."""
    reviews = Review.objects.select_related('reviewer', 'tutor', 'session').order_by('-created_at')[:50]

    data = []
    for r in reviews:
        data.append({
            'id': r.pk, 'reviewer': r.reviewer.get_full_name(),
            'tutor': r.tutor.get_full_name(),
            'session': r.session.title, 'rating': r.rating,
            'comment': r.comment, 'created': r.created_at.strftime('%b %d, %Y'),
        })

    return JsonResponse({'reviews': data})


# ==================== NOTIFICATION / ANNOUNCEMENT ====================

@csrf_exempt
@admin_required
def admin_api_send_notification(request):
    """Send platform announcement to all users or specific role."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    data = json.loads(request.body)
    title = data.get('title', '').strip()
    message = data.get('message', '').strip()
    target = data.get('target', 'all')  # all, tutors, learners

    if not title or not message:
        return JsonResponse({'error': 'Title and message required'}, status=400)

    users = User.objects.filter(is_active=True)
    if target == 'tutors':
        users = users.filter(profile__role='tutor')
    elif target == 'learners':
        users = users.filter(profile__role='learner')

    count = 0
    for user in users:
        Notification.create_notification(user, 'session_reminder', title, message, '/dashboard/')
        count += 1

    return JsonResponse({'success': True, 'message': f'Notification sent to {count} users.'})


# ==================== ANALYTICS ====================

@admin_required
def admin_api_analytics(request):
    """Platform analytics data for charts."""
    today = timezone.now().date()

    # User growth (last 12 weeks)
    user_growth = []
    for i in range(11, -1, -1):
        week_start = today - timedelta(weeks=i, days=today.weekday())
        week_end = week_start + timedelta(days=6)
        count = User.objects.filter(date_joined__date__gte=week_start, date_joined__date__lte=week_end).count()
        user_growth.append({'label': week_start.strftime('%b %d'), 'value': count})

    # Skill popularity (bookings per skill)
    skill_pop = Skill.objects.annotate(
        booking_count=Count('sessions__bookings')
    ).order_by('-booking_count')[:10]
    skill_data = [{'label': s.name, 'value': s.booking_count} for s in skill_pop]

    # Tutor performance (top 10 by earnings)
    top_tutors = []
    tutors = UserProfile.objects.filter(role='tutor').select_related('user', 'user__wallet')
    for t in tutors:
        earnings = Transaction.objects.filter(
            wallet=t.user.wallet, transaction_type='tutor_earning'
        ).aggregate(total=Sum('amount'))['total'] or 0
        reviews = Review.objects.filter(tutor=t.user).count()
        avg = t.average_rating()
        top_tutors.append({
            'name': t.user.get_full_name(), 'earnings': earnings,
            'reviews': reviews, 'rating': avg, 'trust': t.trust_score,
        })
    top_tutors.sort(key=lambda x: x['earnings'], reverse=True)
    top_tutors = top_tutors[:10]

    # Booking trend (last 12 weeks)
    booking_trend = []
    for i in range(11, -1, -1):
        week_start = today - timedelta(weeks=i, days=today.weekday())
        week_end = week_start + timedelta(days=6)
        count = Booking.objects.filter(booked_at__date__gte=week_start, booked_at__date__lte=week_end).count()
        booking_trend.append({'label': week_start.strftime('%b %d'), 'value': count})

    # Dispute trend
    dispute_count = Booking.objects.filter(is_disputed=True).count()
    resolved_count = Booking.objects.filter(is_disputed=True, dispute_resolved=True).count()

    # Revenue / Credit Purchases Analytics
    all_payments = Payment.objects.filter(status='paid')
    total_revenue = sum(p.amount_inr for p in all_payments) // 100  # in rupees
    total_credits_sold = sum(p.credits for p in all_payments)
    total_paid_orders = all_payments.count()
    failed_orders = Payment.objects.filter(status='failed').count()
    pending_orders = Payment.objects.filter(status='created').count()

    # Revenue trend (last 12 weeks)
    revenue_trend = []
    for i in range(11, -1, -1):
        week_start = today - timedelta(weeks=i, days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_payments = all_payments.filter(paid_at__date__gte=week_start, paid_at__date__lte=week_end)
        week_revenue = sum(p.amount_inr for p in week_payments) // 100
        week_credits = sum(p.credits for p in week_payments)
        revenue_trend.append({
            'label': week_start.strftime('%b %d'),
            'revenue': week_revenue,
            'credits': week_credits,
        })

    # Recent payments (last 10)
    recent_payments = []
    for p in Payment.objects.order_by('-created_at')[:10]:
        recent_payments.append({
            'user': p.user.get_full_name(),
            'amount': p.amount_inr // 100,
            'credits': p.credits,
            'status': p.status,
            'payment_id': p.razorpay_payment_id or '—',
            'date': p.created_at.strftime('%b %d, %I:%M %p'),
        })

    return JsonResponse({
        'user_growth': user_growth,
        'skill_popularity': skill_data,
        'top_tutors': top_tutors,
        'booking_trend': booking_trend,
        'disputes': {'total': dispute_count, 'resolved': resolved_count, 'open': dispute_count - resolved_count},
        'revenue': {
            'total_revenue': total_revenue,
            'total_credits_sold': total_credits_sold,
            'total_orders': total_paid_orders,
            'failed_orders': failed_orders,
            'pending_orders': pending_orders,
        },
        'revenue_trend': revenue_trend,
        'recent_payments': recent_payments,
    })


# ==================== REPORTS ====================

@admin_required
def admin_api_reports(request):
    """List all reports with full data for admin dashboard."""
    reports = SessionReport.objects.select_related(
        'booking', 'reporter', 'tutor', 'booking__session', 'booking__session__skill'
    ).order_by('-created_at')

    data = []
    for r in reports:
        data.append({
            'id': r.pk,
            'report_type': r.get_report_type_display(),
            'report_type_key': r.report_type,
            'reporter': r.reporter.get_full_name(),
            'tutor': r.tutor.get_full_name(),
            'tutor_id': r.tutor.pk,
            'session': r.booking.session.title,
            'skill': r.booking.session.skill.name,
            'description': r.description,
            'evidence_link': r.evidence_link,
            'has_evidence_file': bool(r.evidence_file),
            'evidence_file_url': r.evidence_file.url if r.evidence_file else '',

            # Session tracking
            'session_date': r.session_date.strftime('%b %d, %Y'),
            'scheduled_time': f'{r.session_scheduled_start.strftime("%H:%M")}-{r.session_scheduled_end.strftime("%H:%M")}',
            'actual_duration': r.session_actual_duration,
            'tutor_joined': r.tutor_joined,
            'has_zoom': r.has_zoom_meeting,
            'chat_messages': r.chat_message_count,
            'learner_msgs': r.learner_message_count,
            'tutor_msgs': r.tutor_message_count,
            'credits': r.booking.credits_paid,

            # Flags
            'flag_no_show': r.flag_no_show,
            'flag_short_session': r.flag_short_session,
            'flag_no_engagement': r.flag_no_engagement,
            'flag_payment_issue': r.flag_payment_issue,
            'flag_repeat_offender': r.flag_repeat_offender,
            'auto_score': r.auto_score,

            # Verdict
            'verdict': r.verdict,
            'verdict_display': r.get_verdict_display(),
            'verdict_reason': r.verdict_reason,

            # Tutor response
            'tutor_response': r.tutor_response,
            'has_tutor_evidence': bool(r.tutor_evidence_file),
            'tutor_evidence_url': r.tutor_evidence_file.url if r.tutor_evidence_file else '',
            'tutor_responded_at': r.tutor_responded_at.strftime('%b %d, %I:%M %p') if r.tutor_responded_at else '',

            # Tutor history
            'tutor_stats': r.tutor_past_stats(),

            # Admin
            'admin_notes': r.admin_notes,
            'resolved_at': r.resolved_at.strftime('%b %d, %I:%M %p') if r.resolved_at else '',
            'created_at': r.created_at.strftime('%b %d, %I:%M %p'),
        })

    return JsonResponse({'reports': data})


@csrf_exempt
@admin_required
def admin_api_report_action(request, report_id):
    """Admin takes action on a report."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    report = get_object_or_404(SessionReport, pk=report_id)
    data = json.loads(request.body)
    action = data.get('action', '')
    admin_notes = data.get('admin_notes', '')

    if action == 'mark_valid':
        report.verdict = 'valid'
        report.admin_notes = admin_notes
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        # Refund learner
        booking = report.booking
        wallet = booking.learner.wallet
        wallet.balance += booking.credits_paid
        wallet.save()
        Transaction.objects.create(
            wallet=wallet, transaction_type='credit',
            amount=booking.credits_paid,
            description=f'Refund: Report validated — {booking.session.title}',
            balance_after=wallet.balance,
        )
        booking.status = 'cancelled'
        booking.dispute_resolved = True
        booking.save()

        Notification.create_notification(
            booking.learner, 'credits_refunded',
            'Report resolved — credits refunded',
            f'Your report for "{booking.session.title}" was validated. {booking.credits_paid} credits refunded.',
            '/wallet/'
        )
        Notification.create_notification(
            report.tutor, 'dispute_resolved',
            'Report resolved against you',
            f'A report for "{booking.session.title}" was found valid. Please improve your sessions.',
            '/my-sessions/'
        )

        return JsonResponse({'success': True, 'message': 'Report marked VALID. Learner refunded.'})

    elif action == 'mark_invalid':
        report.verdict = 'invalid'
        report.admin_notes = admin_notes
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        booking = report.booking
        booking.is_disputed = False
        booking.dispute_resolved = True
        booking.save()

        Notification.create_notification(
            booking.learner, 'dispute_resolved',
            'Report dismissed',
            f'Your report for "{booking.session.title}" was reviewed and dismissed.',
            '/my-sessions/'
        )
        Notification.create_notification(
            report.tutor, 'dispute_resolved',
            'Report dismissed in your favor',
            f'A report for "{booking.session.title}" was found invalid. No action taken.',
            '/my-sessions/'
        )

        return JsonResponse({'success': True, 'message': 'Report marked INVALID. Dismissed.'})

    elif action == 'request_tutor_response':
        report.verdict = 'tutor_response_pending'
        report.admin_notes = admin_notes
        report.save()

        Notification.create_notification(
            report.tutor, 'dispute_opened',
            'Admin requests your response to a report',
            f'Please respond to the report for "{report.booking.session.title}" with your explanation and evidence.',
            f'/respond-report/{report.pk}/'
        )

        return JsonResponse({'success': True, 'message': 'Tutor notified. Awaiting response.'})

    return JsonResponse({'error': 'Unknown action'}, status=400)
