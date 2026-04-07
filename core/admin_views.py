"""
Skillify Custom Admin Panel Views
All AJAX-powered API endpoints for the admin dashboard.
"""
import io
import json
from datetime import timedelta, datetime, date
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
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


# ==================== ADMIN MANAGEMENT ====================

@admin_required
def admin_api_admins(request):
    """List all current admins (staff users)."""
    admins = User.objects.filter(is_staff=True).select_related('profile').order_by('-date_joined')
    data = []
    for u in admins:
        try:
            avatar = u.profile.avatar_url()
            role = u.profile.role
        except UserProfile.DoesNotExist:
            avatar = ''
            role = '—'
        data.append({
            'id': u.pk,
            'name': u.get_full_name() or u.username,
            'email': u.email,
            'role': role,
            'is_superuser': u.is_superuser,
            'joined': u.date_joined.strftime('%b %d, %Y'),
            'avatar': avatar,
        })
    return JsonResponse({'admins': data, 'total': len(data)})


@csrf_exempt
@admin_required
def admin_api_admin_create(request):
    """Create a new admin user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    data = json.loads(request.body)
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not full_name or not email or not password:
        return JsonResponse({'error': 'Full name, email, and password are required'}, status=400)
    if len(password) < 6:
        return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'A user with this email already exists'}, status=400)

    parts = full_name.split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
        is_staff=True,
    )

    # Ensure profile exists with role=tutor (signal usually creates one)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = 'tutor'
    profile.is_verified = True
    profile.save()

    # Ensure wallet exists with 100 credits
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': 100})
    if wallet.balance < 100:
        wallet.balance = 100
        wallet.save()

    Notification.create_notification(
        user, 'session_reminder',
        'Welcome to Skillify Admin',
        f'You have been added as an admin by {request.user.get_full_name() or request.user.username}.',
        '/panel/'
    )

    return JsonResponse({
        'success': True,
        'message': f'Admin "{full_name}" created successfully.',
        'admin': {
            'id': user.pk,
            'name': full_name,
            'email': email,
        }
    })


@csrf_exempt
@admin_required
def admin_api_admin_remove(request, user_id):
    """Remove admin access from a user (sets is_staff=False; does NOT delete)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = get_object_or_404(User, pk=user_id)

    if user.pk == request.user.pk:
        return JsonResponse({'error': 'You cannot remove your own admin access'}, status=400)
    if user.is_superuser:
        return JsonResponse({'error': 'Cannot remove admin from a superuser'}, status=400)

    user.is_staff = False
    user.save()

    Notification.create_notification(
        user, 'session_reminder',
        'Admin access removed',
        f'Your admin access has been revoked by {request.user.get_full_name() or request.user.username}.',
        '/dashboard/'
    )

    return JsonResponse({'success': True, 'message': f'Admin access removed from {user.get_full_name() or user.username}.'})


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


# ==================== PDF REPORT GENERATION ====================

def _get_date_range(request):
    """Resolve ?period=... &from=...&to=... into (start_date, end_date, label)."""
    period = request.GET.get('period', 'all')
    today = timezone.now().date()
    if period == 'today':
        return today, today, 'Today'
    if period == '7days':
        return today - timedelta(days=7), today, 'Last 7 Days'
    if period == 'month':
        return today - timedelta(days=30), today, 'Last Month'
    if period == '3months':
        return today - timedelta(days=90), today, 'Last 3 Months'
    if period == 'year':
        return today - timedelta(days=365), today, 'Last Year'
    if period == 'custom':
        try:
            df = datetime.strptime(request.GET.get('from', ''), '%Y-%m-%d').date()
            dt = datetime.strptime(request.GET.get('to', ''), '%Y-%m-%d').date()
            return df, dt, f'{df.strftime("%b %d, %Y")} → {dt.strftime("%b %d, %Y")}'
        except (ValueError, TypeError):
            return None, None, 'All Time'
    return None, None, 'All Time'


@login_required
@user_passes_test(is_admin)
def generate_pdf_report(request):
    """Generate a PDF report based on type + date range and return as download."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.pdfgen import canvas

    report_type = request.GET.get('type', 'full')
    start_date, end_date, period_label = _get_date_range(request)

    # Skillify teal theme
    TEAL = colors.HexColor('#4ECDC4')
    TEAL_DARK = colors.HexColor('#3BABA3')
    DARK = colors.HexColor('#2D3748')
    MUTED = colors.HexColor('#718096')
    LIGHT = colors.HexColor('#F0F4F8')

    buffer = io.BytesIO()

    def header_footer(canv, doc):
        """Draw the teal header bar + footer with page number on every page."""
        canv.saveState()
        page_w, page_h = A4
        # Header bar
        canv.setFillColor(TEAL)
        canv.rect(0, page_h - 22 * mm, page_w, 22 * mm, fill=1, stroke=0)
        canv.setFillColor(colors.white)
        canv.setFont('Helvetica-Bold', 18)
        canv.drawString(15 * mm, page_h - 12 * mm, 'Skillify')
        canv.setFont('Helvetica', 9)
        canv.drawString(15 * mm, page_h - 18 * mm, 'Learn Skills. Share Knowledge.')
        canv.setFont('Helvetica-Bold', 10)
        canv.drawRightString(page_w - 15 * mm, page_h - 12 * mm, 'Admin Report')
        canv.setFont('Helvetica', 8)
        canv.drawRightString(
            page_w - 15 * mm, page_h - 17 * mm,
            f'Generated: {timezone.now().strftime("%b %d, %Y %H:%M")}'
        )
        # Footer
        canv.setStrokeColor(TEAL)
        canv.setLineWidth(1)
        canv.line(15 * mm, 15 * mm, page_w - 15 * mm, 15 * mm)
        canv.setFillColor(MUTED)
        canv.setFont('Helvetica', 8)
        canv.drawString(15 * mm, 10 * mm, '© Skillify Platform — Confidential')
        canv.drawRightString(page_w - 15 * mm, 10 * mm, f'Page {doc.page}')
        canv.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=30 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleS', parent=styles['Heading1'], fontSize=20, textColor=DARK,
        alignment=0, spaceAfter=4, fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubS', parent=styles['Normal'], fontSize=10, textColor=MUTED, spaceAfter=14
    )
    section_style = ParagraphStyle(
        'SectS', parent=styles['Heading2'], fontSize=13, textColor=TEAL_DARK,
        spaceAfter=8, spaceBefore=14, fontName='Helvetica-Bold'
    )

    titles_map = {
        'full': 'Full Platform Report',
        'users': 'Users Report',
        'sessions': 'Sessions Report',
        'bookings': 'Bookings Report',
        'revenue': 'Revenue Report',
        'tutors': 'Tutors Report',
        'reviews': 'Reviews Report',
        'reports_summary': 'Session Reports Summary',
    }
    report_title = titles_map.get(report_type, 'Skillify Report')

    story = []
    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(f'Period: <b>{period_label}</b>', subtitle_style))

    def make_table(headers, rows, col_widths=None):
        data = [headers] + rows
        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TEAL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 1), (-1, -1), DARK),
        ]))
        return tbl

    def make_summary(items):
        """4-column stat summary cards."""
        rows = []
        row = []
        for label, value in items:
            row.append([
                Paragraph(f'<font size=14 color="#3BABA3"><b>{value}</b></font>', styles['Normal']),
                Paragraph(f'<font size=8 color="#718096">{label.upper()}</font>', styles['Normal']),
            ])
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            while len(row) < 4:
                row.append(['', ''])
            rows.append(row)

        for r in rows:
            cells = []
            for cell in r:
                if isinstance(cell, list):
                    sub = Table([[cell[0]], [cell[1]]], colWidths=[42 * mm])
                    sub.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
                        ('BOX', (0, 0), (-1, -1), 1, TEAL),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    cells.append(sub)
                else:
                    cells.append('')
            outer = Table([cells], colWidths=[44 * mm] * 4)
            outer.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            story.append(outer)
            story.append(Spacer(1, 6))

    # Filter helper for date range
    def filter_qs(qs, field):
        if start_date and end_date:
            return qs.filter(**{f'{field}__date__gte': start_date, f'{field}__date__lte': end_date})
        return qs

    def filter_qs_date(qs, field):
        if start_date and end_date:
            return qs.filter(**{f'{field}__gte': start_date, f'{field}__lte': end_date})
        return qs

    # ============ DATA SECTIONS ============

    def section_users():
        story.append(Paragraph('Users', section_style))
        users_qs = filter_qs(User.objects.select_related('profile', 'wallet'), 'date_joined').order_by('-date_joined')
        rows = []
        for u in users_qs[:200]:
            try:
                role = u.profile.get_role_display()
                bal = u.wallet.balance
            except Exception:
                role, bal = '—', 0
            sessions = Booking.objects.filter(learner=u).count()
            rows.append([
                u.get_full_name() or u.username,
                u.email[:30],
                role,
                u.date_joined.strftime('%b %d, %Y'),
                str(sessions),
                str(bal),
            ])
        story.append(make_table(
            ['Name', 'Email', 'Role', 'Joined', 'Bookings', 'Balance'],
            rows or [['No data', '', '', '', '', '']],
            col_widths=[35 * mm, 45 * mm, 18 * mm, 25 * mm, 20 * mm, 20 * mm],
        ))

    def section_sessions():
        story.append(Paragraph('Sessions', section_style))
        sess_qs = filter_qs(Session.objects.select_related('tutor', 'skill'), 'created_at').order_by('-date')
        rows = []
        for s in sess_qs[:200]:
            rows.append([
                s.title[:32],
                (s.tutor.get_full_name() or s.tutor.username)[:22],
                s.skill.name[:18],
                s.date.strftime('%b %d, %Y'),
                s.status,
                str(s.bookings.count()),
            ])
        story.append(make_table(
            ['Session', 'Tutor', 'Skill', 'Date', 'Status', 'Bookings'],
            rows or [['No data', '', '', '', '', '']],
            col_widths=[50 * mm, 35 * mm, 25 * mm, 25 * mm, 22 * mm, 18 * mm],
        ))

    def section_bookings():
        story.append(Paragraph('Bookings', section_style))
        b_qs = filter_qs(Booking.objects.select_related('learner', 'session', 'session__tutor'), 'booked_at').order_by('-booked_at')
        rows = []
        for b in b_qs[:200]:
            rows.append([
                (b.learner.get_full_name() or b.learner.username)[:22],
                (b.session.tutor.get_full_name() or b.session.tutor.username)[:22],
                b.session.title[:30],
                b.status,
                str(b.credits_paid),
                b.booked_at.strftime('%b %d'),
            ])
        story.append(make_table(
            ['Learner', 'Tutor', 'Session', 'Status', 'Credits', 'Date'],
            rows or [['No data', '', '', '', '', '']],
            col_widths=[32 * mm, 32 * mm, 45 * mm, 25 * mm, 18 * mm, 22 * mm],
        ))

    def section_revenue():
        story.append(Paragraph('Revenue (Razorpay Payments)', section_style))
        p_qs = filter_qs(Payment.objects.filter(status='paid').select_related('user'), 'created_at').order_by('-created_at')
        total_revenue = sum(p.amount_inr for p in p_qs) // 100
        total_credits = sum(p.credits for p in p_qs)
        make_summary([
            ('Total Revenue', f'₹{total_revenue}'),
            ('Credits Sold', str(total_credits)),
            ('Paid Orders', str(p_qs.count())),
            ('Avg Order', f'₹{total_revenue // p_qs.count() if p_qs.count() else 0}'),
        ])
        rows = []
        for p in p_qs[:150]:
            rows.append([
                (p.user.get_full_name() or p.user.username)[:25],
                f'₹{p.amount_inr // 100}',
                str(p.credits),
                (p.razorpay_payment_id or '—')[:22],
                p.created_at.strftime('%b %d, %Y'),
            ])
        story.append(make_table(
            ['User', 'Amount', 'Credits', 'Payment ID', 'Date'],
            rows or [['No data', '', '', '', '']],
            col_widths=[42 * mm, 22 * mm, 22 * mm, 48 * mm, 28 * mm],
        ))

    def section_tutors():
        story.append(Paragraph('Tutors', section_style))
        tutors = UserProfile.objects.filter(role='tutor').select_related('user', 'user__wallet')
        rows = []
        for t in tutors[:200]:
            earnings = Transaction.objects.filter(
                wallet=t.user.wallet, transaction_type='tutor_earning'
            ).aggregate(total=Sum('amount'))['total'] or 0
            sessions_done = Session.objects.filter(tutor=t.user, status='completed').count()
            rows.append([
                (t.user.get_full_name() or t.user.username)[:25],
                f'{t.average_rating()}/5',
                str(sessions_done),
                f'{t.trust_score:.0f}/100',
                str(earnings),
            ])
        story.append(make_table(
            ['Tutor', 'Avg Rating', 'Sessions', 'Trust', 'Earnings'],
            rows or [['No data', '', '', '', '']],
            col_widths=[55 * mm, 25 * mm, 25 * mm, 25 * mm, 32 * mm],
        ))

    def section_reviews():
        story.append(Paragraph('Reviews', section_style))
        r_qs = filter_qs(Review.objects.select_related('reviewer', 'tutor', 'session'), 'created_at').order_by('-created_at')
        rows = []
        for r in r_qs[:200]:
            rows.append([
                f'{r.rating}/5 ★',
                (r.tutor.get_full_name() or r.tutor.username)[:22],
                (r.reviewer.get_full_name() or r.reviewer.username)[:22],
                (r.comment[:48] + '…') if len(r.comment) > 48 else (r.comment or '—'),
                r.created_at.strftime('%b %d, %Y'),
            ])
        story.append(make_table(
            ['Rating', 'Tutor', 'Reviewer', 'Comment', 'Date'],
            rows or [['No data', '', '', '', '']],
            col_widths=[18 * mm, 32 * mm, 32 * mm, 60 * mm, 25 * mm],
        ))

    def section_reports_summary():
        story.append(Paragraph('Session Reports Summary', section_style))
        rep_qs = filter_qs(SessionReport.objects.select_related('reporter', 'tutor', 'booking__session'), 'created_at').order_by('-created_at')
        rows = []
        for r in rep_qs[:200]:
            rows.append([
                r.get_report_type_display()[:20],
                (r.tutor.get_full_name() or r.tutor.username)[:22],
                (r.reporter.get_full_name() or r.reporter.username)[:22],
                r.get_verdict_display()[:20],
                str(r.auto_score),
                r.created_at.strftime('%b %d'),
            ])
        story.append(make_table(
            ['Type', 'Tutor', 'Reporter', 'Verdict', 'Score', 'Date'],
            rows or [['No data', '', '', '', '', '']],
            col_widths=[32 * mm, 30 * mm, 30 * mm, 32 * mm, 18 * mm, 22 * mm],
        ))

    def section_full_summary():
        story.append(Paragraph('Platform Overview', section_style))
        users_count = filter_qs(User.objects.all(), 'date_joined').count()
        sess_count = filter_qs(Session.objects.all(), 'created_at').count()
        book_count = filter_qs(Booking.objects.all(), 'booked_at').count()
        rev_qs = filter_qs(Payment.objects.filter(status='paid'), 'created_at')
        revenue = sum(p.amount_inr for p in rev_qs) // 100
        tutor_count = UserProfile.objects.filter(role='tutor').count()
        review_count = filter_qs(Review.objects.all(), 'created_at').count()
        disputes = Booking.objects.filter(is_disputed=True).count()
        credits_in = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
        make_summary([
            ('Users', str(users_count)),
            ('Tutors', str(tutor_count)),
            ('Sessions', str(sess_count)),
            ('Bookings', str(book_count)),
            ('Revenue', f'₹{revenue}'),
            ('Reviews', str(review_count)),
            ('Disputes', str(disputes)),
            ('Credits', str(credits_in)),
        ])

        # Top tutors
        story.append(Paragraph('Top Tutors by Earnings', section_style))
        top_rows = []
        for t in UserProfile.objects.filter(role='tutor').select_related('user', 'user__wallet')[:50]:
            earnings = Transaction.objects.filter(
                wallet=t.user.wallet, transaction_type='tutor_earning'
            ).aggregate(total=Sum('amount'))['total'] or 0
            top_rows.append((earnings, [
                (t.user.get_full_name() or t.user.username)[:30],
                f'{t.average_rating()}/5',
                str(t.user.tutor_sessions.filter(status='completed').count()),
                str(earnings),
            ]))
        top_rows.sort(key=lambda x: -x[0])
        story.append(make_table(
            ['Tutor', 'Rating', 'Sessions', 'Earnings'],
            [r[1] for r in top_rows[:10]] or [['No data', '', '', '']],
            col_widths=[70 * mm, 30 * mm, 30 * mm, 35 * mm],
        ))

        # Recent revenue
        story.append(Paragraph('Recent Revenue', section_style))
        rows = []
        for p in rev_qs.select_related('user').order_by('-created_at')[:10]:
            rows.append([
                (p.user.get_full_name() or p.user.username)[:25],
                f'₹{p.amount_inr // 100}',
                str(p.credits),
                p.created_at.strftime('%b %d, %Y'),
            ])
        story.append(make_table(
            ['User', 'Amount', 'Credits', 'Date'],
            rows or [['No data', '', '', '']],
            col_widths=[60 * mm, 30 * mm, 30 * mm, 45 * mm],
        ))

    # Dispatch by report type
    if report_type == 'users':
        section_users()
    elif report_type == 'sessions':
        section_sessions()
    elif report_type == 'bookings':
        section_bookings()
    elif report_type == 'revenue':
        section_revenue()
    elif report_type == 'tutors':
        section_tutors()
    elif report_type == 'reviews':
        section_reviews()
    elif report_type == 'reports_summary':
        section_reports_summary()
    else:  # full
        section_full_summary()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    pdf_data = buffer.getvalue()
    buffer.close()

    filename = f'skillify_{report_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
