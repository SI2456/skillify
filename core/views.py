import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.core.mail import send_mail
from django.conf import settings

from .models import (
    Skill, UserProfile, Session, Booking, Review, Wallet, Transaction,
    Conversation, Message, Notification, TutorAvailability, SessionMaterial, Payment,
    SessionReport
)
from .forms import RegisterForm, LoginForm, OTPForm, ProfileEditForm, SessionForm, ReviewForm


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


# ==================== PUBLIC PAGES ====================

def index(request):
    skills = Skill.objects.all()
    tutor_count = UserProfile.objects.filter(role='tutor', is_verified=True).count()
    session_count = Session.objects.filter(status='completed').count()
    skill_count = Skill.objects.count()
    context = {
        'skills': skills,
        'tutor_count': tutor_count,
        'session_count': session_count,
        'skill_count': skill_count,
    }
    return render(request, 'core/index.html', context)


# ==================== AUTH ====================

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            names = data['fullName'].split(' ', 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''

            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password'],
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )
            profile = user.profile
            profile.role = data['role']
            otp = generate_otp()
            profile.otp = otp
            profile.otp_created_at = timezone.now()
            profile.save()

            # Send OTP email (branded HTML)
            try:
                from .email_service import send_otp_email
                send_otp_email(data['email'], otp, 'verify your account')
            except Exception:
                pass  # Console backend in dev

            request.session['verify_email'] = data['email']
            messages.success(request, f'OTP sent to {data["email"]}. Please verify.')
            return redirect('verify_otp')
        else:
            for error in form.errors.values():
                messages.error(request, error[0] if isinstance(error, list) else error)
    return render(request, 'core/register.html')


def verify_otp_view(request):
    email = request.session.get('verify_email')
    if not email:
        messages.error(request, 'No email to verify.')
        return redirect('register')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            try:
                user = User.objects.get(email=email)
                profile = user.profile
                if profile.otp == otp:
                    if profile.otp_created_at and (timezone.now() - profile.otp_created_at).seconds <= 300:
                        user.is_active = True
                        user.save()
                        profile.is_verified = True
                        profile.otp = ''
                        profile.save()
                        del request.session['verify_email']
                        messages.success(request, 'Email verified! You can now login.')
                        return redirect('login')
                    else:
                        messages.error(request, 'OTP has expired. Please request a new one.')
                else:
                    messages.error(request, 'Invalid OTP. Please try again.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
    return render(request, 'core/verify_otp.html', {'email': email})


def resend_otp_view(request):
    email = request.session.get('verify_email')
    if not email:
        return redirect('register')
    try:
        user = User.objects.get(email=email)
        profile = user.profile
        otp = generate_otp()
        profile.otp = otp
        profile.otp_created_at = timezone.now()
        profile.save()
        try:
            send_mail(
                'Skillify - New OTP',
                f'Your new OTP verification code is: {otp}\n\nThis code expires in 5 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception:
            pass
        messages.success(request, 'New OTP sent!')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
    return redirect('verify_otp')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            role = form.cleaned_data.get('role', 'learner')

            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email.')
                return render(request, 'core/login.html')

            if not user_obj.is_active:
                profile = user_obj.profile
                if not profile.is_verified:
                    request.session['verify_email'] = email
                    messages.error(request, 'Please verify your email first.')
                    return redirect('verify_otp')

            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                profile = user.profile
                if role:
                    profile.role = role
                    profile.save()
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('index')


# ==================== FORGOT / RESET PASSWORD ====================

def forgot_password_view(request):
    """Step 1: User enters email → OTP is sent."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'core/forgot_password.html')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            return render(request, 'core/forgot_password.html')

        # Generate OTP and save to profile
        profile = user.profile
        otp = generate_otp()
        profile.otp = otp
        profile.otp_created_at = timezone.now()
        profile.save()

        # Send OTP via email (branded HTML)
        try:
            from .email_service import send_otp_email
            send_otp_email(email, otp, 'reset your password')
        except Exception:
            pass  # Console backend in dev

        # Store email in session for next step
        request.session['reset_email'] = email
        messages.success(request, f'OTP sent to {email}. Check your inbox (or console in dev mode).')
        return redirect('reset_password')

    return render(request, 'core/forgot_password.html')


def reset_password_view(request):
    """Step 2: User enters OTP + new password → password is changed."""
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please request a password reset first.')
        return redirect('forgot_password')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validate inputs
        if not otp or not new_password:
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'core/reset_password.html', {'email': email})

        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'core/reset_password.html', {'email': email})

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/reset_password.html', {'email': email})

        try:
            user = User.objects.get(email=email)
            profile = user.profile

            # Verify OTP
            if profile.otp != otp:
                messages.error(request, 'Invalid OTP. Please try again.')
                return render(request, 'core/reset_password.html', {'email': email})

            # Check expiry (5 minutes)
            if profile.otp_created_at and (timezone.now() - profile.otp_created_at).seconds > 300:
                messages.error(request, 'OTP has expired. Please request a new one.')
                return redirect('forgot_password')

            # Reset password
            user.set_password(new_password)
            user.save()

            # Clear OTP
            profile.otp = ''
            profile.otp_created_at = None
            profile.save()

            # Clear session
            if 'reset_email' in request.session:
                del request.session['reset_email']

            messages.success(request, 'Password changed successfully! You can now login with your new password.')
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('forgot_password')

    return render(request, 'core/reset_password.html', {'email': email})


def resend_reset_otp_view(request):
    """Resend OTP for password reset."""
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please start the password reset process first.')
        return redirect('forgot_password')

    try:
        user = User.objects.get(email=email)
        profile = user.profile
        otp = generate_otp()
        profile.otp = otp
        profile.otp_created_at = timezone.now()
        profile.save()

        try:
            from .email_service import send_otp_email
            send_otp_email(email, otp, 'reset your password')
        except Exception:
            pass

        messages.success(request, f'New OTP sent to {email}!')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('forgot_password')

    return redirect('reset_password')


# ==================== DASHBOARD ====================

@login_required
def dashboard_view(request):
    profile = request.user.profile
    wallet = request.user.wallet
    bookings = Booking.objects.filter(learner=request.user).select_related('session', 'session__tutor', 'session__skill')
    tutor_sessions = Session.objects.filter(tutor=request.user) if profile.role == 'tutor' else None

    upcoming_bookings = bookings.filter(
        status__in=['confirmed', 'tutor_completed', 'learner_completed'],
        session__status__in=['upcoming', 'tutor_completed']
    ).order_by('session__date')[:5]
    completed_bookings = bookings.filter(status__in=['completed', 'pending_review'])

    # Tutor stats
    tutor_stats = {}
    if profile.role == 'tutor':
        tutor_stats = {
            'total_sessions': Session.objects.filter(tutor=request.user).count(),
            'avg_rating': Review.objects.filter(tutor=request.user).aggregate(avg=Avg('rating'))['avg'] or 0,
            'total_students': Booking.objects.filter(session__tutor=request.user).values('learner').distinct().count(),
        }

    context = {
        'profile': profile,
        'wallet': wallet,
        'upcoming_bookings': upcoming_bookings,
        'completed_bookings': completed_bookings,
        'tutor_sessions': tutor_sessions,
        'tutor_stats': tutor_stats,
    }
    return render(request, 'core/dashboard.html', context)


# ==================== ROLE SWITCHING ====================

@login_required
def switch_role(request):
    profile = request.user.profile
    profile.role = 'tutor' if profile.role == 'learner' else 'learner'
    profile.save()
    messages.success(request, f'Switched to {profile.get_role_display()} mode.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ==================== BROWSE SKILLS ====================

@login_required
def browse_skills_view(request):
    # Only learners can browse skills
    profile = request.user.profile
    if profile.role == 'tutor':
        messages.info(request, 'Switch to Learner mode to browse and book sessions.')
        return redirect('dashboard')

    sessions = Session.objects.filter(status='upcoming', date__gte=timezone.now().date()).select_related(
        'tutor', 'skill', 'tutor__profile'
    ).annotate(
        tutor_avg_rating=Avg('tutor__reviews_received__rating'),
    )

    # Search
    search = request.GET.get('search', '')
    if search:
        sessions = sessions.filter(
            Q(title__icontains=search) |
            Q(skill__name__icontains=search) |
            Q(tutor__first_name__icontains=search) |
            Q(tutor__last_name__icontains=search)
        )

    # Skill filter
    skill_filter = request.GET.get('skill', '')
    if skill_filter:
        sessions = sessions.filter(skill__name=skill_filter)

    # Session type filter
    session_type = request.GET.get('type', '')
    if session_type:
        sessions = sessions.filter(session_type=session_type)

    # Level filter
    level_filter = request.GET.get('level', '')
    if level_filter:
        sessions = sessions.filter(level=level_filter)

    # Price range filter
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    if price_min:
        try:
            sessions = sessions.filter(credits_required__gte=int(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            sessions = sessions.filter(credits_required__lte=int(price_max))
        except ValueError:
            pass

    # Rating filter
    min_rating = request.GET.get('rating', '')
    if min_rating:
        try:
            sessions = sessions.filter(tutor_avg_rating__gte=float(min_rating))
        except ValueError:
            pass

    # Date filter
    date_filter = request.GET.get('date', '')
    if date_filter:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            sessions = sessions.filter(date=filter_date)
        except ValueError:
            pass

    # Sort
    sort_by = request.GET.get('sort', 'soonest')
    if sort_by == 'price_low':
        sessions = sessions.order_by('credits_required', 'date')
    elif sort_by == 'price_high':
        sessions = sessions.order_by('-credits_required', 'date')
    elif sort_by == 'highest_rated':
        sessions = sessions.order_by('-tutor_avg_rating', 'date')
    elif sort_by == 'newest':
        sessions = sessions.order_by('-created_at')
    else:  # soonest (default)
        sessions = sessions.order_by('date', 'start_time')

    skills = Skill.objects.all()
    wallet = request.user.wallet

    context = {
        'sessions': sessions,
        'skills': skills,
        'search': search,
        'skill_filter': skill_filter,
        'session_type': session_type,
        'level_filter': level_filter,
        'price_min': price_min,
        'price_max': price_max,
        'min_rating': min_rating,
        'date_filter': date_filter,
        'sort_by': sort_by,
        'wallet': wallet,
        'profile': profile,
    }
    return render(request, 'core/browse_skills.html', context)


# ==================== TUTOR PROFILE ====================

def tutor_profile_view(request, user_id):
    tutor_user = get_object_or_404(User, pk=user_id)
    profile = tutor_user.profile
    sessions = Session.objects.filter(tutor=tutor_user, status='upcoming').select_related('skill').order_by('date', 'start_time')
    reviews = Review.objects.filter(tutor=tutor_user).select_related('reviewer', 'reviewer__profile', 'session', 'session__skill').order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    review_count = reviews.count()

    # Rating breakdown (5 star → 1 star, ordered)
    rating_breakdown = []
    for i in range(5, 0, -1):
        count = reviews.filter(rating=i).count()
        pct = round((count / review_count) * 100) if review_count > 0 else 0
        rating_breakdown.append({'stars': i, 'count': count, 'pct': pct})

    # Get embeddable video URL for YouTube/Vimeo
    embed_video_url = profile.get_embed_video_url()

    # Build weekly calendar data per skill (Preply style)
    from datetime import date, timedelta
    import json as json_module

    today = date.today()
    # Week starts from today, show 7 days
    week_start = today
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    # Group sessions by skill
    skills_with_sessions = {}
    for session in sessions:
        if session.date < today:
            continue
        if session.date > week_dates[-1]:
            continue

        skill_name = session.skill.name
        if skill_name not in skills_with_sessions:
            skills_with_sessions[skill_name] = {
                'skill': session.skill,
                'slots': {},  # date_str -> list of session dicts
            }

        date_str = session.date.isoformat()
        if date_str not in skills_with_sessions[skill_name]['slots']:
            skills_with_sessions[skill_name]['slots'][date_str] = []

        # Check if already booked by current user
        already_booked = False
        if request.user.is_authenticated:
            already_booked = Booking.objects.filter(learner=request.user, session=session).exists()

        skills_with_sessions[skill_name]['slots'][date_str].append({
            'id': session.pk,
            'time': session.start_time.strftime('%H:%M'),
            'end_time': session.end_time.strftime('%H:%M'),
            'credits': session.credits_required,
            'title': session.title,
            'already_booked': already_booked,
            'spots_left': session.max_participants - session.bookings.count(),
        })

    # Build calendar JSON for JS
    calendar_data = {}
    for skill_name, data in skills_with_sessions.items():
        calendar_data[skill_name] = {}
        for date_str, slot_list in data['slots'].items():
            calendar_data[skill_name][date_str] = slot_list

    # User wallet balance
    user_balance = 0
    if request.user.is_authenticated:
        user_balance = request.user.wallet.balance

    context = {
        'tutor_user': tutor_user,
        'profile': profile,
        'sessions': sessions,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_count': review_count,
        'rating_breakdown': rating_breakdown,
        'embed_video_url': embed_video_url,
        'week_dates': week_dates,
        'skills_with_sessions': skills_with_sessions,
        'calendar_json': json_module.dumps(calendar_data),
        'user_balance': user_balance,
        'sessions_completed': Session.objects.filter(tutor=tutor_user, status='completed').count(),
        'total_students': Booking.objects.filter(session__tutor=tutor_user).values('learner').distinct().count(),
    }
    return render(request, 'core/tutor_profile.html', context)


# ==================== EDIT TUTOR PROFILE ====================

@login_required
def edit_tutor_profile_view(request):
    profile = request.user.profile

    # Block editing if currently in learner mode
    if profile.role == 'learner':
        messages.error(request, 'Switch to Tutor mode to edit your profile.')
        return redirect('dashboard')

    skills = Skill.objects.all()

    if request.method == 'POST':
        full_name = request.POST.get('fullName', '')
        if full_name:
            names = full_name.split(' ', 1)
            request.user.first_name = names[0]
            request.user.last_name = names[1] if len(names) > 1 else ''
            request.user.save()

        profile.bio = request.POST.get('bio', profile.bio)
        profile.expertise = request.POST.get('headline', profile.expertise)
        profile.demo_video = request.POST.get('demo_video', profile.demo_video)
        profile.linkedin = request.POST.get('linkedin', profile.linkedin)
        profile.github = request.POST.get('github', profile.github)

        # Experience & Education
        exp_years = request.POST.get('experience_years', '0')
        profile.experience_years = int(exp_years) if exp_years.isdigit() else 0
        profile.education = request.POST.get('education', profile.education)
        profile.show_experience = request.POST.get('show_experience') == 'on'
        profile.show_education = request.POST.get('show_education') == 'on'

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        # Handle remove profile picture
        if request.POST.get('remove_picture') == '1':
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
                profile.profile_picture = None

        # Handle certificate upload
        if 'certificate' in request.FILES:
            profile.certificate = request.FILES['certificate']
        profile.certificate_title = request.POST.get('certificate_title', profile.certificate_title)
        if request.POST.get('remove_certificate') == '1':
            if profile.certificate:
                profile.certificate.delete(save=False)
                profile.certificate = None
            profile.certificate_title = ''

        skill_ids = request.POST.getlist('skills')
        profile.skills.set(skill_ids)  # Works even if empty list (clears all)

        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('edit_tutor_profile')

    context = {
        'profile': profile,
        'skills': skills,
    }
    return render(request, 'core/edit_tutor_profile.html', context)


@login_required
def learner_profile_view(request):
    """Learner views/edits their own profile."""
    profile = request.user.profile
    skills = Skill.objects.all()

    if request.method == 'POST':
        full_name = request.POST.get('fullName', '')
        if full_name:
            names = full_name.split(' ', 1)
            request.user.first_name = names[0]
            request.user.last_name = names[1] if len(names) > 1 else ''
            request.user.save()

        profile.bio = request.POST.get('bio', profile.bio)
        profile.learning_interests = request.POST.get('learning_interests', profile.learning_interests)
        profile.skill_level = request.POST.get('skill_level', profile.skill_level)

        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        if request.POST.get('remove_picture') == '1':
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
                profile.profile_picture = None

        skill_ids = request.POST.getlist('interests')
        profile.skills.set(skill_ids)

        profile.save()
        messages.success(request, 'Profile updated!')
        return redirect('learner_profile')

    # Stats
    total_bookings = Booking.objects.filter(learner=request.user).count()
    completed_sessions = Booking.objects.filter(learner=request.user, status__in=['completed', 'pending_review']).count()
    total_spent = sum(
        b.credits_paid for b in Booking.objects.filter(learner=request.user, status__in=['confirmed', 'completed', 'pending_review'])
    )

    context = {
        'profile': profile,
        'skills': skills,
        'total_bookings': total_bookings,
        'completed_sessions': completed_sessions,
        'total_spent': total_spent,
    }
    return render(request, 'core/learner_profile.html', context)


# ==================== SESSIONS ====================

@login_required
def my_sessions_view(request):
    profile = request.user.profile
    wallet = request.user.wallet

    if profile.role == 'tutor':
        sessions = Session.objects.filter(tutor=request.user).select_related('skill').order_by('-date')
        bookings = Booking.objects.filter(session__tutor=request.user).select_related(
            'learner', 'session', 'session__skill'
        )
    else:
        bookings = Booking.objects.filter(learner=request.user).select_related(
            'session', 'session__tutor', 'session__skill'
        )
        sessions = None

    upcoming = bookings.filter(
        status__in=['confirmed', 'tutor_completed', 'learner_completed', 'disputed'],
        session__status__in=['upcoming', 'tutor_completed']
    ).order_by('session__date') if profile.role == 'learner' else None
    completed = bookings.filter(status__in=['completed', 'pending_review']) if profile.role == 'learner' else None

    context = {
        'profile': profile,
        'wallet': wallet,
        'sessions': sessions,
        'bookings': bookings,
        'upcoming_bookings': upcoming,
        'completed_bookings': completed,
    }
    return render(request, 'core/my_session.html', context)


@login_required
def create_session_view(request):
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.tutor = request.user

            # Validate: no past date/time
            from datetime import datetime, date
            now = timezone.localtime()
            session_start = timezone.make_aware(
                datetime.combine(session.date, session.start_time)
            )

            if session.date < now.date():
                messages.error(request, 'Cannot create a session in the past. Please select a future date.')
                skills = Skill.objects.all()
                return render(request, 'core/create_session.html', {'form': form, 'skills': skills})

            if session.date == now.date() and session.start_time <= now.time():
                messages.error(request, 'Start time must be in the future. Please select a later time.')
                skills = Skill.objects.all()
                return render(request, 'core/create_session.html', {'form': form, 'skills': skills})

            if session.end_time <= session.start_time:
                messages.error(request, 'End time must be after start time.')
                skills = Skill.objects.all()
                return render(request, 'core/create_session.html', {'form': form, 'skills': skills})

            session.save()
            messages.success(request, 'Session created successfully!')
            return redirect('my_sessions')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SessionForm()

    skills = Skill.objects.all()
    context = {'form': form, 'skills': skills}
    return render(request, 'core/create_session.html', context)


# ==================== BOOKING ====================

@login_required
def book_session_view(request, session_id):
    session = get_object_or_404(Session, pk=session_id, status='upcoming')
    wallet = request.user.wallet
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if session.tutor == request.user:
        if is_ajax:
            return JsonResponse({'success': False, 'error': "You can't book your own session."})
        messages.error(request, "You can't book your own session.")
        return redirect('browse_skills')

    if Booking.objects.filter(learner=request.user, session=session).exists():
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'You already booked this session.', 'already_booked': True})
        messages.error(request, 'You already booked this session.')
        return redirect('my_sessions')

    # Check if session is full (one-to-one = max 1 booking)
    current_bookings = session.bookings.filter(status__in=['confirmed', 'tutor_completed', 'learner_completed']).count()
    if current_bookings >= session.max_participants:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Session is full. No spots available.', 'session_full': True})
        messages.error(request, 'This session is full. No spots available.')
        return redirect('browse_skills')

    if wallet.balance < session.credits_required:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Insufficient credits.',
                'insufficient_credits': True,
                'balance': wallet.balance,
                'required': session.credits_required,
                'shortfall': session.credits_required - wallet.balance,
            })
        messages.error(request, 'Insufficient credits.')
        return redirect('wallet')

    # Deduct credits
    wallet.balance -= session.credits_required
    wallet.save()
    Transaction.objects.create(
        wallet=wallet,
        transaction_type='booking_payment',
        amount=session.credits_required,
        description=f'Booking: {session.title}',
        balance_after=wallet.balance,
    )

    Booking.objects.create(
        learner=request.user,
        session=session,
        status='confirmed',
        credits_paid=session.credits_required,
    )

    # Get the booking we just created
    booking = Booking.objects.get(learner=request.user, session=session)

    # Create Zoom meeting (only on first booking, if not already created)
    if not session.zoom_join_url:
        from .zoom_service import create_zoom_meeting, is_zoom_configured
        if is_zoom_configured():
            zoom_result = create_zoom_meeting(session)
            if zoom_result['success']:
                session.zoom_meeting_id = zoom_result['meeting_id']
                session.zoom_join_url = zoom_result['join_url']
                session.zoom_start_url = zoom_result['start_url']
                session.zoom_password = zoom_result['password']
                session.save()

    # Send email notifications
    from .email_service import notify_tutor_new_booking, notify_learners_booking_confirmation
    notify_tutor_new_booking(booking)
    notify_learners_booking_confirmation(booking)

    # In-app notifications
    _notify(session.tutor, 'booking_new',
            f'New booking: {session.title}',
            f'{request.user.get_full_name()} booked your session on {session.date.strftime("%b %d")}',
            '/my-sessions/')
    _notify(request.user, 'booking_confirmed',
            f'Booking confirmed: {session.title}',
            f'Session with {session.tutor.get_full_name()} on {session.date.strftime("%b %d")} at {session.start_time.strftime("%H:%M")}',
            '/my-sessions/')

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': f'Session booked! {session.credits_required} credits deducted.',
            'new_balance': wallet.balance,
            'session_title': session.title,
            'session_date': session.date.strftime('%b %d'),
            'session_time': session.start_time.strftime('%H:%M'),
        })

    messages.success(request,
        f'Session "{session.title}" booked! {session.credits_required} credits deducted. '
        f'Confirmation email sent. Check My Sessions for details.'
    )
    return redirect('my_sessions')


# ==================== DUAL CONFIRMATION SYSTEM ====================

@login_required
def tutor_complete_session_view(request, session_id):
    """Tutor clicks Complete Session — only allowed after session end time."""
    session = get_object_or_404(Session, pk=session_id, tutor=request.user)

    # Check if session time has passed
    from datetime import datetime, date
    now = timezone.localtime()
    session_end = timezone.make_aware(
        datetime.combine(session.date, session.end_time)
    )
    if now < session_end:
        messages.error(request,
            f'You can only mark complete after the session ends ({session.end_time.strftime("%I:%M %p")}). '
            f'Please wait until the session is over.'
        )
        return redirect('my_sessions')

    bookings = Booking.objects.filter(session=session, status__in=['confirmed', 'learner_completed'])

    if not bookings.exists():
        messages.error(request, 'No active bookings found for this session.')
        return redirect('my_sessions')

    all_done = True
    for booking in bookings:
        booking.tutor_confirmed = True
        booking.tutor_confirmed_at = timezone.now()
        if booking.learner_confirmed:
            booking.check_dual_completion()
        else:
            booking.status = 'tutor_completed'
            booking.save()
            all_done = False

    if all_done:
        session.status = 'completed'
        session.save()
        messages.success(request, 'Session completed! Both sides confirmed — credits transferred to your wallet.')
    else:
        messages.success(request,
            'Session marked complete. Waiting for learner(s) to confirm. '
            'Credits auto-release in 30 minutes if no response.'
        )

    return redirect('my_sessions')


@login_required
def learner_complete_session_view(request, booking_id):
    """Learner clicks Confirm Complete — marks their side done."""
    booking = get_object_or_404(Booking, pk=booking_id, learner=request.user)

    if booking.is_disputed:
        messages.error(request, 'This booking is under dispute. Please wait for admin review.')
        return redirect('my_sessions')

    if booking.status in ('completed', 'pending_review'):
        messages.info(request, 'This session is already completed.')
        return redirect('my_sessions')

    booking.learner_confirmed = True
    booking.learner_confirmed_at = timezone.now()

    if booking.tutor_confirmed:
        booking.check_dual_completion()
        session = booking.session
        pending = session.bookings.filter(
            status__in=['confirmed', 'tutor_completed', 'learner_completed']
        ).count()
        if pending == 0:
            session.status = 'completed'
            session.save()
        messages.success(request, 'Session confirmed! Credits released to tutor. You can now leave a review.')
    else:
        booking.status = 'learner_completed'
        booking.save()
        messages.success(request, 'You confirmed the session. Waiting for tutor to confirm.')

    return redirect('my_sessions')


@login_required
def report_issue_view(request, booking_id):
    """Learner reports fraud — pauses credit transfer for admin review."""
    booking = get_object_or_404(Booking, pk=booking_id, learner=request.user)

    if booking.status in ('completed', 'pending_review'):
        messages.error(request, 'This session is already completed.')
        return redirect('my_sessions')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for the dispute.')
            return redirect('my_sessions')

        booking.is_disputed = True
        booking.dispute_reason = reason
        booking.dispute_created_at = timezone.now()
        booking.status = 'disputed'
        booking.save()

        messages.warning(request, 'Issue reported. Credit transfer is paused. Admin will review your case.')

    return redirect('my_sessions')


@login_required
def start_session_view(request, session_id):
    """
    Tutor clicks "Start Session" →
    1. Create Zoom meeting if not already created
    2. Email Zoom link to ALL booked learners
    3. Redirect tutor to Zoom start_url (host link)
    """
    session = get_object_or_404(Session, pk=session_id, tutor=request.user, status='upcoming')

    # Step 1: Create Zoom meeting if not exists
    if not session.zoom_join_url:
        from .zoom_service import create_zoom_meeting, is_zoom_configured
        if is_zoom_configured():
            zoom_result = create_zoom_meeting(session)
            if zoom_result['success']:
                session.zoom_meeting_id = zoom_result['meeting_id']
                session.zoom_join_url = zoom_result['join_url']
                session.zoom_start_url = zoom_result['start_url']
                session.zoom_password = zoom_result['password']
                session.save()
            else:
                messages.error(request,
                    f'Could not create Zoom meeting: {zoom_result["error"]}. '
                    f'Please check your Zoom API settings.'
                )
                return redirect('my_sessions')
        else:
            messages.error(request,
                'Zoom is not configured. Please set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, '
                'ZOOM_CLIENT_SECRET in your environment variables.'
            )
            return redirect('my_sessions')

    # Step 2: Email Zoom link to all booked learners
    from .email_service import notify_learners_session_starting
    emails_sent = notify_learners_session_starting(session)

    if emails_sent > 0:
        messages.success(request,
            f'Session started! Zoom link emailed to {emails_sent} learner(s). '
            f'Redirecting you to Zoom...'
        )
    else:
        messages.info(request, 'No learners to notify. Redirecting to Zoom...')

    # Step 3: Redirect tutor to Zoom (host link)
    if session.zoom_start_url:
        return redirect(session.zoom_start_url)
    elif session.zoom_join_url:
        return redirect(session.zoom_join_url)
    else:
        messages.error(request, 'No Zoom link available.')
        return redirect('my_sessions')


# ==================== REVIEWS ====================

@login_required
def submit_review_view(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    booking = get_object_or_404(Booking, learner=request.user, session=session)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if Review.objects.filter(session=session, reviewer=request.user).exists():
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'You already reviewed this session.'})
        messages.error(request, 'You already reviewed this session.')
        return redirect('my_sessions')

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()

        if 1 <= rating <= 5:
            review = Review.objects.create(
                session=session,
                reviewer=request.user,
                tutor=session.tutor,
                rating=rating,
                comment=comment,
            )
            booking.status = 'completed'
            booking.save()

            # Update tutor trust score (comprehensive formula)
            session.tutor.profile.trust_score = session.tutor.profile.calculate_trust_score()
            session.tutor.profile.save()

            # Notify tutor about new review
            _notify(session.tutor, 'review_received',
                    f'New {rating}⭐ review!',
                    f'{request.user.get_full_name()} rated your "{session.title}" session',
                    f'/tutor/{session.tutor.pk}/')

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Review submitted! Thank you.',
                    'review': {
                        'rating': rating,
                        'comment': comment,
                        'reviewer_name': request.user.get_full_name(),
                        'created_at': review.created_at.strftime('%B %d, %Y'),
                        'tutor_avg_rating': round(avg, 1),
                        'tutor_review_count': Review.objects.filter(tutor=session.tutor).count(),
                    }
                })

            messages.success(request, 'Review submitted! Thank you.')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Please select a rating between 1 and 5.'})
            messages.error(request, 'Please select a rating between 1 and 5.')

    return redirect('my_sessions')


# ==================== WALLET & PAYMENTS ====================

@login_required
def wallet_view(request):
    wallet = request.user.wallet
    transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:20]
    profile = request.user.profile

    # Date filter
    from datetime import timedelta
    date_filter = request.GET.get('period', 'all')
    today = timezone.now().date()

    if date_filter == 'week':
        transactions = transactions.filter(created_at__date__gte=today - timedelta(days=7))
    elif date_filter == 'month':
        transactions = transactions.filter(created_at__date__gte=today - timedelta(days=30))
    elif date_filter == '3months':
        transactions = transactions.filter(created_at__date__gte=today - timedelta(days=90))
    elif date_filter == 'year':
        transactions = transactions.filter(created_at__date__gte=today - timedelta(days=365))

    # Type filter
    txn_type = request.GET.get('type', '')
    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)

    context = {
        'wallet': wallet,
        'transactions': transactions,
        'payments': payments,
        'profile': profile,
        'packages': settings.CREDIT_PACKAGES,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'date_filter': date_filter,
        'txn_type': txn_type,
    }
    return render(request, 'core/wallet.html', context)


@login_required
def create_razorpay_order(request):
    """Create a Razorpay order for credit top-up."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    import json
    data = json.loads(request.body)
    package_id = data.get('package_id', '')

    # Find package
    package = None
    for pkg in settings.CREDIT_PACKAGES:
        if pkg['id'] == package_id:
            package = pkg
            break

    if not package:
        return JsonResponse({'error': 'Invalid package'}, status=400)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({'error': 'Razorpay not configured. Contact admin.'}, status=400)

    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order (amount in paise)
    try:
        order_data = {
            'amount': package['inr'] * 100,  # paise
            'currency': 'INR',
            'receipt': f'skillify_{request.user.pk}_{package_id}',
            'notes': {
                'user_id': request.user.pk,
                'credits': package['credits'],
                'package': package_id,
            }
        }
        razorpay_order = client.order.create(data=order_data)

        # Save payment record
        Payment.objects.create(
            user=request.user,
            razorpay_order_id=razorpay_order['id'],
            amount_inr=package['inr'] * 100,
            credits=package['credits'],
            status='created',
        )

        return JsonResponse({
            'success': True,
            'order_id': razorpay_order['id'],
            'amount': package['inr'] * 100,
            'currency': 'INR',
            'credits': package['credits'],
            'key': settings.RAZORPAY_KEY_ID,
            'user_name': request.user.get_full_name(),
            'user_email': request.user.email,
        })

    except Exception as e:
        return JsonResponse({'error': f'Payment error: {str(e)}'}, status=500)


@login_required
def verify_razorpay_payment(request):
    """Verify Razorpay payment signature and add credits."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    import json
    data = json.loads(request.body)

    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_signature = data.get('razorpay_signature', '')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse({'error': 'Missing payment data'}, status=400)

    # Get payment record
    try:
        payment = Payment.objects.get(razorpay_order_id=razorpay_order_id, user=request.user)
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)

    if payment.status == 'paid':
        return JsonResponse({'error': 'Payment already processed'}, status=400)

    # Verify signature
    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        payment.status = 'failed'
        payment.save()
        return JsonResponse({'error': 'Payment verification failed. Signature mismatch.'}, status=400)

    # Payment verified — add credits
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = 'paid'
    payment.paid_at = timezone.now()
    payment.save()

    # Add credits to wallet
    wallet = request.user.wallet
    wallet.balance += payment.credits
    wallet.save()

    Transaction.objects.create(
        wallet=wallet,
        transaction_type='razorpay_topup',
        amount=payment.credits,
        description=f'Top-up: ₹{payment.amount_inr // 100} → {payment.credits} credits',
        balance_after=wallet.balance,
        payment_id=razorpay_payment_id,
    )

    # Notify user
    _notify(
        request.user, 'credits_received',
        f'{payment.credits} credits added!',
        f'Payment of ₹{payment.amount_inr // 100} successful. {payment.credits} credits added to your wallet.',
        '/wallet/'
    )

    return JsonResponse({
        'success': True,
        'message': f'{payment.credits} credits added to your wallet!',
        'new_balance': wallet.balance,
        'payment_id': razorpay_payment_id,
    })


# ==================== REPORTS ====================

@login_required
def file_report_view(request, booking_id):
    """Learner files a detailed report against a session."""
    booking = get_object_or_404(Booking, pk=booking_id, learner=request.user)
    session = booking.session

    # Check if report already exists
    if hasattr(booking, 'report'):
        messages.info(request, 'You already filed a report for this session.')
        return redirect('my_sessions')

    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'other')
        description = request.POST.get('description', '').strip()
        evidence_link = request.POST.get('evidence_link', '').strip()
        evidence_file = request.FILES.get('evidence_file', None)

        if not description:
            messages.error(request, 'Please describe the issue.')
            return redirect('my_sessions')

        # Auto-capture session tracking data
        conversation = Conversation.get_or_create_conversation(request.user, session.tutor)
        chat_count = 0
        learner_msgs = 0
        tutor_msgs = 0
        if conversation:
            chat_count = conversation.messages.count()
            learner_msgs = conversation.messages.filter(sender=request.user).count()
            tutor_msgs = conversation.messages.filter(sender=session.tutor).count()

        # Calculate actual session duration (if Zoom was used)
        actual_duration = 0
        if session.zoom_meeting_id:
            from datetime import datetime
            scheduled_mins = (datetime.combine(datetime.today(), session.end_time) -
                            datetime.combine(datetime.today(), session.start_time)).total_seconds() / 60
            actual_duration = int(scheduled_mins)  # Approximate — Zoom API would give exact

        report = SessionReport.objects.create(
            booking=booking,
            reporter=request.user,
            tutor=session.tutor,
            report_type=report_type,
            description=description,
            evidence_link=evidence_link,
            evidence_file=evidence_file,
            session_date=session.date,
            session_scheduled_start=session.start_time,
            session_scheduled_end=session.end_time,
            session_actual_duration=actual_duration,
            tutor_joined=bool(session.zoom_meeting_id),
            chat_message_count=chat_count,
            learner_message_count=learner_msgs,
            tutor_message_count=tutor_msgs,
            payment_status='paid' if booking.credits_paid > 0 else 'none',
            has_zoom_meeting=bool(session.zoom_meeting_id),
        )

        # Run auto-verification
        verdict = report.run_auto_verification()

        # Update booking status
        booking.is_disputed = True
        booking.dispute_reason = f"[{report.get_report_type_display()}] {description}"
        booking.dispute_created_at = timezone.now()
        booking.save()

        # Notify admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            _notify(admin_user, 'dispute_opened',
                    f'New Report: {report.get_report_type_display()}',
                    f'{request.user.get_full_name()} reported {session.tutor.get_full_name()} for "{session.title}". Auto-verdict: {report.get_verdict_display()}',
                    '/panel/')

        # Notify tutor
        _notify(session.tutor, 'dispute_opened',
                f'Report filed against your session',
                f'A learner reported an issue with "{session.title}". An admin will review this.',
                '/my-sessions/')

        messages.success(request, f'Report filed successfully. System verdict: {report.get_verdict_display()}. Admin will review shortly.')
        return redirect('my_sessions')

    context = {
        'booking': booking,
        'session': session,
        'report_types': SessionReport.REPORT_TYPE_CHOICES,
    }
    return render(request, 'core/file_report.html', context)


@login_required
def tutor_respond_report(request, report_id):
    """Tutor submits response to a report."""
    report = get_object_or_404(SessionReport, pk=report_id, tutor=request.user, verdict='tutor_response_pending')

    if request.method == 'POST':
        response_text = request.POST.get('response', '').strip()
        evidence = request.FILES.get('evidence_file', None)

        if not response_text:
            messages.error(request, 'Please provide your explanation.')
            return redirect('my_sessions')

        report.tutor_response = response_text
        if evidence:
            report.tutor_evidence_file = evidence
        report.tutor_responded_at = timezone.now()
        report.verdict = 'needs_review'
        report.save()

        # Notify admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            _notify(admin_user, 'dispute_opened',
                    f'Tutor responded to Report #{report.pk}',
                    f'{request.user.get_full_name()} submitted evidence for "{report.booking.session.title}".',
                    '/panel/')

        messages.success(request, 'Your response has been submitted. Admin will make a final decision.')
        return redirect('my_sessions')

    context = {'report': report}
    return render(request, 'core/tutor_respond_report.html', context)


# ==================== RESCHEDULE ====================

@login_required
def tutor_reschedule_session(request, session_id):
    """Tutor requests reschedule — must be 45+ min before session."""
    session = get_object_or_404(Session, pk=session_id, tutor=request.user, status='upcoming')

    from datetime import datetime, timedelta
    now = timezone.localtime()
    session_start = timezone.make_aware(datetime.combine(session.date, session.start_time))
    minutes_until = (session_start - now).total_seconds() / 60

    if minutes_until < 45:
        messages.error(request, 'You can only reschedule at least 45 minutes before the session starts.')
        return redirect('my_sessions')

    if request.method == 'POST':
        new_date = request.POST.get('new_date', '')
        new_start = request.POST.get('new_start', '')
        new_end = request.POST.get('new_end', '')
        reason = request.POST.get('reason', '').strip()

        if not all([new_date, new_start, new_end]):
            messages.error(request, 'Please fill all reschedule fields.')
            return redirect('my_sessions')

        try:
            from datetime import datetime as dt_cls
            new_date_obj = dt_cls.strptime(new_date, '%Y-%m-%d').date()
            new_start_obj = dt_cls.strptime(new_start, '%H:%M').time()
            new_end_obj = dt_cls.strptime(new_end, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Invalid date/time format.')
            return redirect('my_sessions')

        if new_end_obj <= new_start_obj:
            messages.error(request, 'End time must be after start time.')
            return redirect('my_sessions')

        # Update all bookings for this session
        bookings = session.bookings.filter(status='confirmed')
        if not bookings.exists():
            messages.error(request, 'No active bookings to reschedule.')
            return redirect('my_sessions')

        for booking in bookings:
            booking.reschedule_status = 'pending'
            booking.reschedule_new_date = new_date_obj
            booking.reschedule_new_start = new_start_obj
            booking.reschedule_new_end = new_end_obj
            booking.reschedule_reason = reason
            booking.reschedule_requested_at = timezone.now()
            booking.save()

            # Notify each learner
            _notify(
                booking.learner, 'session_reminder',
                f'Reschedule Request: {session.title}',
                f'{session.tutor.get_full_name()} wants to reschedule to {new_date} at {new_start}. Reason: {reason or "Not specified"}. You have 30 min to respond.',
                '/my-sessions/'
            )

        messages.success(request, f'Reschedule request sent to {bookings.count()} learner(s). They have 30 minutes to respond.')
        return redirect('my_sessions')

    return redirect('my_sessions')


@login_required
def learner_respond_reschedule(request, booking_id):
    """Learner accepts or rejects reschedule."""
    booking = get_object_or_404(Booking, pk=booking_id, learner=request.user, reschedule_status='pending')
    session = booking.session

    if request.method != 'POST':
        return redirect('my_sessions')

    action = request.POST.get('action', '')

    if action == 'accept':
        booking.reschedule_status = 'accepted'
        booking.save()

        # Check if ALL learners in this session have responded
        _check_reschedule_completion(session)

        _notify(
            session.tutor, 'booking_confirmed',
            f'{booking.learner.get_full_name()} accepted reschedule',
            f'Your session "{session.title}" reschedule was accepted.',
            '/my-sessions/'
        )
        messages.success(request, 'Reschedule accepted! Session time updated.')

    elif action == 'reject':
        booking.reschedule_status = 'rejected'
        booking.status = 'cancelled'
        booking.save()

        # Refund credits
        _refund_booking(booking)

        _notify(
            session.tutor, 'booking_new',
            f'{booking.learner.get_full_name()} rejected reschedule',
            f'Reschedule rejected for "{session.title}". Credits refunded to learner.',
            '/my-sessions/'
        )
        messages.success(request, 'Reschedule rejected. Your credits have been refunded.')

        # Check if all learners rejected (cancel session)
        _check_reschedule_completion(session)

    return redirect('my_sessions')


def _refund_booking(booking):
    """Refund credits for a cancelled/rejected booking."""
    wallet = booking.learner.wallet
    wallet.balance += booking.credits_paid
    wallet.save()
    Transaction.objects.create(
        wallet=wallet,
        transaction_type='credit',
        amount=booking.credits_paid,
        description=f'Refund: Reschedule rejected — {booking.session.title}',
        balance_after=wallet.balance,
    )
    _notify(
        booking.learner, 'credits_refunded',
        f'{booking.credits_paid} credits refunded',
        f'Reschedule for "{booking.session.title}" was rejected. Credits returned.',
        '/wallet/'
    )


def _check_reschedule_completion(session):
    """Check if all learners responded to reschedule. Update session accordingly."""
    pending_bookings = session.bookings.filter(reschedule_status='pending')
    if pending_bookings.exists():
        return  # Still waiting for responses

    accepted = session.bookings.filter(reschedule_status='accepted')
    all_bookings = session.bookings.exclude(reschedule_status='none')

    if accepted.exists():
        # At least one accepted — update session time from first accepted booking
        first = accepted.first()
        session.date = first.reschedule_new_date
        session.start_time = first.reschedule_new_start
        session.end_time = first.reschedule_new_end
        session.save()
    else:
        # All rejected — cancel session
        session.status = 'cancelled'
        session.save()
        _notify(
            session.tutor, 'dispute_opened',
            f'Session cancelled: {session.title}',
            f'All learners rejected the reschedule. Session has been cancelled.',
            '/my-sessions/'
        )


# ==================== MESSAGES ====================

@login_required
def inbox_view(request):
    """Show all conversations for the current user."""
    conversations = Conversation.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related('user1', 'user2', 'user1__profile', 'user2__profile')

    # Build conversation data with unread counts
    conv_data = []
    total_unread = 0
    for conv in conversations:
        other = conv.other_user(request.user)
        unread = conv.unread_count(request.user)
        total_unread += unread
        last_msg = conv.last_message()
        conv_data.append({
            'conversation': conv,
            'other_user': other,
            'unread': unread,
            'last_message': last_msg,
        })

    # Get list of users this person can message
    profile = request.user.profile
    if profile.role == 'learner':
        booked_tutor_ids = Booking.objects.filter(
            learner=request.user
        ).values_list('session__tutor_id', flat=True).distinct()
        contactable_users = User.objects.filter(pk__in=booked_tutor_ids).exclude(pk=request.user.pk)
    else:
        learner_ids = Booking.objects.filter(
            session__tutor=request.user
        ).values_list('learner_id', flat=True).distinct()
        contactable_users = User.objects.filter(pk__in=learner_ids).exclude(pk=request.user.pk)

    # Always include admin as contactable for help
    admin_user = User.objects.filter(is_superuser=True).first()

    context = {
        'conversations': conv_data,
        'total_unread': total_unread,
        'contactable_users': contactable_users,
        'profile': profile,
        'admin_user': admin_user,
    }
    return render(request, 'core/inbox.html', context)


@login_required
def contact_admin_view(request):
    """Create/open a conversation with admin for help."""
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        messages.error(request, 'No admin available. Please try again later.')
        return redirect('inbox')

    if admin_user == request.user:
        messages.info(request, 'You are the admin!')
        return redirect('inbox')

    # Create or get conversation with admin
    Conversation.get_or_create_conversation(request.user, admin_user)

    # Send auto intro message if first time
    conv = Conversation.get_or_create_conversation(request.user, admin_user)
    if conv and conv.messages.count() == 0:
        Message.objects.create(
            conversation=conv,
            sender=admin_user,
            content=f'Hi {request.user.first_name}! 👋 Welcome to Skillify Support. How can I help you today? Feel free to ask anything about the platform, sessions, payments, or any issues you\'re facing.',
        )

    return redirect('chat', user_id=admin_user.pk)


@login_required
def chat_view(request, user_id):
    """Chat page with a specific user."""
    other_user = get_object_or_404(User, pk=user_id)

    if other_user == request.user:
        messages.error(request, "You can't message yourself.")
        return redirect('inbox')

    # Get or create conversation
    conversation = Conversation.get_or_create_conversation(request.user, other_user)

    # Mark messages from other user as read
    conversation.messages.filter(sender=other_user, is_read=False).update(is_read=True)

    # Get messages
    chat_messages = conversation.messages.select_related('sender', 'sender__profile').order_by('created_at')

    context = {
        'conversation': conversation,
        'other_user': other_user,
        'chat_messages': chat_messages,
        'profile': request.user.profile,
    }
    return render(request, 'core/chat.html', context)


@login_required
def send_message_view(request, user_id):
    """AJAX endpoint to send a message with optional file attachment."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        return JsonResponse({'error': "Can't message yourself"}, status=400)

    content = request.POST.get('content', '').strip()
    attachment = request.FILES.get('attachment', None)

    if not content and not attachment:
        return JsonResponse({'error': 'Message or file required'}, status=400)
    if content and len(content) > 2000:
        return JsonResponse({'error': 'Message too long (max 2000 chars)'}, status=400)

    # File size check (max 10MB)
    if attachment and attachment.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (max 10MB)'}, status=400)

    conversation = Conversation.get_or_create_conversation(request.user, other_user)

    msg = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
        attachment=attachment,
    )

    conversation.save()

    # Build response
    msg_data = {
        'id': msg.pk,
        'content': msg.content,
        'sender_name': request.user.get_full_name(),
        'sender_avatar': request.user.profile.avatar_url(),
        'is_mine': True,
        'time': msg.created_at.strftime('%I:%M %p'),
        'attachment': None,
    }
    if msg.attachment:
        msg_data['attachment'] = {
            'url': msg.attachment.url,
            'filename': msg.attachment_filename(),
            'is_image': msg.is_image(),
        }

    return JsonResponse({'success': True, 'message': msg_data})


@login_required
def fetch_messages_view(request, user_id):
    """AJAX polling endpoint — fetch new messages since last_id."""
    other_user = get_object_or_404(User, pk=user_id)
    conversation = Conversation.get_or_create_conversation(request.user, other_user)

    last_id = int(request.GET.get('last_id', 0))

    new_messages = conversation.messages.filter(pk__gt=last_id).select_related('sender', 'sender__profile')

    # Mark incoming messages as read
    new_messages.filter(sender=other_user, is_read=False).update(is_read=True)

    msg_list = []
    for msg in new_messages:
        m = {
            'id': msg.pk,
            'content': msg.content,
            'sender_name': msg.sender.get_full_name(),
            'sender_avatar': msg.sender.profile.avatar_url(),
            'is_mine': msg.sender == request.user,
            'time': msg.created_at.strftime('%I:%M %p'),
            'attachment': None,
        }
        if msg.attachment:
            m['attachment'] = {
                'url': msg.attachment.url,
                'filename': msg.attachment_filename(),
                'is_image': msg.is_image(),
            }
        msg_list.append(m)

    return JsonResponse({'messages': msg_list})


@login_required
def unread_count_view(request):
    """AJAX endpoint — return total unread message count for navbar badge."""
    count = Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ),
        is_read=False,
    ).exclude(sender=request.user).count()

    return JsonResponse({'unread': count})


# ==================== API ENDPOINTS (DRF) ====================

@login_required
def api_switch_role(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.role = 'tutor' if profile.role == 'learner' else 'learner'
        profile.save()
        return JsonResponse({'status': 'ok', 'role': profile.role})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def api_book_session(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(Session, pk=session_id, status='upcoming')
        wallet = request.user.wallet

        if session.tutor == request.user:
            return JsonResponse({'error': "Can't book own session"}, status=400)
        if Booking.objects.filter(learner=request.user, session=session).exists():
            return JsonResponse({'error': 'Already booked'}, status=400)
        if wallet.balance < session.credits_required:
            return JsonResponse({'error': 'Insufficient credits'}, status=400)

        wallet.balance -= session.credits_required
        wallet.save()
        Transaction.objects.create(
            wallet=wallet,
            transaction_type='booking_payment',
            amount=session.credits_required,
            description=f'Booking: {session.title}',
            balance_after=wallet.balance,
        )
        Booking.objects.create(
            learner=request.user,
            session=session,
            status='confirmed',
            credits_paid=session.credits_required,
        )
        return JsonResponse({'status': 'ok', 'balance': wallet.balance})
    return JsonResponse({'error': 'POST required'}, status=400)


# ==================== REGISTRATION API (AJAX) ====================

import json
from django.views.decorators.http import require_GET


@require_GET
def api_check_email(request):
    """Check if email already exists in database. Returns JSON."""
    email = request.GET.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'exists': False})

    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists, 'email': email})


def api_register(request):
    """AJAX registration endpoint. Creates user + sends OTP. No page reload."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)

    try:
        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {
                'fullName': request.POST.get('fullName', ''),
                'email': request.POST.get('email', ''),
                'password': request.POST.get('password', ''),
                'confirmPassword': request.POST.get('confirmPassword', ''),
                'role': request.POST.get('role', 'learner'),
            }

        full_name = data.get('fullName', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        role = data.get('role', 'learner')

        # Server-side validations
        errors = {}

        if not full_name or len(full_name) < 2:
            errors['fullName'] = 'Full name is required (min 2 characters).'

        if not email:
            errors['email'] = 'Email is required.'
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors['email'] = 'Please enter a valid email address.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'An account with this email already exists.'

        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters.'

        if password != confirm_password:
            errors['confirmPassword'] = 'Passwords do not match.'

        if role not in ('learner', 'tutor'):
            errors['role'] = 'Invalid role selected.'

        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # Create user
        names = full_name.split(' ', 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ''

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )

        profile = user.profile
        profile.role = role
        otp = generate_otp()
        profile.otp = otp
        profile.otp_created_at = timezone.now()
        profile.save()

        # Send OTP email (branded HTML)
        try:
            from .email_service import send_otp_email
            send_otp_email(email, otp, 'verify your account')
        except Exception:
            pass

        # Store email in session for OTP verification
        request.session['verify_email'] = email

        return JsonResponse({
            'success': True,
            'message': f'OTP sent to {email}. Redirecting to verification...',
            'redirect': '/verify-otp/',
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== NOTIFICATIONS ====================

@login_required
def notifications_api(request):
    """AJAX: Get notifications for bell icon dropdown."""
    # Count unread FIRST (before slicing)
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # Then get latest 20 for display
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]

    data = []
    for n in notifs:
        data.append({
            'id': n.pk,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'time': n.created_at.strftime('%b %d, %I:%M %p'),
            'time_ago': _time_ago(n.created_at),
        })

    return JsonResponse({'notifications': data, 'unread_count': unread_count})


from django.views.decorators.csrf import csrf_exempt as _notif_csrf

@_notif_csrf
@login_required
def mark_notification_read(request, notif_id):
    """Mark a single notification as read."""
    notif = get_object_or_404(Notification, pk=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'success': True})


@_notif_csrf
@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


def _time_ago(dt):
    """Human-readable time ago string."""
    from django.utils import timezone as tz
    diff = tz.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        return f'{int(seconds//60)}m ago'
    elif seconds < 86400:
        return f'{int(seconds//3600)}h ago'
    elif seconds < 604800:
        return f'{int(seconds//86400)}d ago'
    else:
        return dt.strftime('%b %d')


def _notify(user, ntype, title, message, link=''):
    """Helper to create notification."""
    Notification.create_notification(user, ntype, title, message, link)


# ==================== TUTOR AVAILABILITY ====================

@login_required
def manage_availability_view(request):
    """Tutor sets weekly recurring availability."""
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, 'Switch to Tutor mode to manage availability.')
        return redirect('dashboard')

    skills = profile.skills.all()
    availability = TutorAvailability.objects.filter(tutor=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            day = int(request.POST.get('day', 0))
            start = request.POST.get('start_time', '')
            end = request.POST.get('end_time', '')
            skill_id = request.POST.get('skill', '')
            credits = int(request.POST.get('credits', 50))

            if start and end and skill_id:
                from datetime import datetime
                start_t = datetime.strptime(start, '%H:%M').time()
                end_t = datetime.strptime(end, '%H:%M').time()

                # Max 1 hour check
                from datetime import timedelta, datetime as dt_cls
                start_dt = dt_cls.combine(dt_cls.today(), start_t)
                end_dt = dt_cls.combine(dt_cls.today(), end_t)
                if (end_dt - start_dt) > timedelta(hours=1):
                    messages.error(request, 'Max slot duration is 1 hour.')
                elif end_t <= start_t:
                    messages.error(request, 'End time must be after start time.')
                else:
                    TutorAvailability.objects.create(
                        tutor=request.user, day_of_week=day,
                        start_time=start_t, end_time=end_t,
                        skill_id=skill_id, credits_per_session=credits,
                    )
                    messages.success(request, 'Availability slot added!')
            else:
                messages.error(request, 'Please fill all fields.')

        elif action == 'delete':
            slot_id = request.POST.get('slot_id', '')
            TutorAvailability.objects.filter(pk=slot_id, tutor=request.user).delete()
            messages.success(request, 'Slot removed.')

        elif action == 'generate':
            # Auto-generate sessions for next 7 days from availability
            generated = _generate_sessions_from_availability(request.user)
            messages.success(request, f'{generated} sessions generated for the next 7 days!')

        return redirect('manage_availability')

    # Group availability by day
    days = {}
    for slot in availability:
        day_name = slot.get_day_of_week_display()
        if day_name not in days:
            days[day_name] = []
        days[day_name].append(slot)

    context = {
        'profile': profile,
        'skills': skills,
        'availability': availability,
        'days': days,
        'day_choices': TutorAvailability.DAY_CHOICES,
    }
    return render(request, 'core/manage_availability.html', context)


def _generate_sessions_from_availability(tutor):
    """Auto-generate Session objects for the next 7 days based on TutorAvailability."""
    from datetime import date, timedelta
    today = date.today()
    slots = TutorAvailability.objects.filter(tutor=tutor, is_active=True)
    count = 0

    for day_offset in range(7):
        d = today + timedelta(days=day_offset)
        weekday = d.weekday()  # 0=Mon, 6=Sun

        for slot in slots.filter(day_of_week=weekday):
            # Check if session already exists for this slot
            exists = Session.objects.filter(
                tutor=tutor, date=d,
                start_time=slot.start_time, end_time=slot.end_time,
                skill=slot.skill,
            ).exists()

            if not exists:
                Session.objects.create(
                    tutor=tutor,
                    title=f'{slot.skill.name} Session',
                    skill=slot.skill,
                    level='all',
                    date=d,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    credits_required=slot.credits_per_session,
                    session_type='one-to-one',
                    max_participants=1,
                    status='upcoming',
                )
                count += 1

    return count


# ==================== SESSION MATERIALS ====================

@login_required
def upload_material_view(request, session_id):
    """Tutor uploads files/PDFs for a session."""
    session = get_object_or_404(Session, pk=session_id, tutor=request.user)

    if request.method == 'POST' and request.FILES.get('file'):
        title = request.POST.get('title', 'Session Material')
        f = request.FILES['file']

        # Max 10MB
        if f.size > 10 * 1024 * 1024:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'File too large (max 10MB).'})
            messages.error(request, 'File too large (max 10MB).')
            return redirect('my_sessions')

        material = SessionMaterial.objects.create(
            session=session, title=title, file=f,
        )

        # Notify booked learners
        for booking in session.bookings.filter(status__in=['confirmed', 'tutor_completed']):
            _notify(
                booking.learner, 'booking_confirmed',
                f'New material for "{session.title}"',
                f'{session.tutor.get_full_name()} uploaded: {title}',
                f'/my-sessions/'
            )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 'material': {
                    'id': material.pk, 'title': material.title,
                    'filename': material.filename(),
                    'url': material.file.url,
                }
            })

        messages.success(request, f'Material "{title}" uploaded!')

    return redirect('my_sessions')


@login_required
def delete_material_view(request, material_id):
    """Tutor deletes a session material. Uses csrf token from JS."""
    material = get_object_or_404(SessionMaterial, pk=material_id, session__tutor=request.user)
    material.file.delete(save=False)
    material.delete()
    return JsonResponse({'success': True})


# ==================== TUTOR EARNINGS DASHBOARD ====================

@login_required
def earnings_dashboard_view(request):
    """Tutor earnings dashboard with Chart.js data."""
    profile = request.user.profile
    if profile.role != 'tutor':
        messages.error(request, 'Switch to Tutor mode to view earnings.')
        return redirect('dashboard')

    from datetime import timedelta
    import json as json_module

    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    ninety_days_ago = today - timedelta(days=90)

    # Earnings transactions
    earnings = Transaction.objects.filter(
        wallet=request.user.wallet,
        transaction_type='tutor_earning',
    )

    # Total stats
    total_earned = sum(t.amount for t in earnings)
    monthly_earned = sum(t.amount for t in earnings.filter(created_at__date__gte=thirty_days_ago))
    weekly_earned = sum(t.amount for t in earnings.filter(created_at__date__gte=today - timedelta(days=7)))

    total_students = Booking.objects.filter(
        session__tutor=request.user
    ).values('learner').distinct().count()

    total_sessions = Session.objects.filter(
        tutor=request.user, status='completed'
    ).count()

    total_reviews = Review.objects.filter(tutor=request.user).count()
    avg_rating = Review.objects.filter(tutor=request.user).aggregate(avg=Avg('rating'))['avg'] or 0

    # Weekly earnings chart (last 12 weeks)
    weekly_data = []
    for i in range(11, -1, -1):
        week_start = today - timedelta(weeks=i, days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_earnings = sum(
            t.amount for t in earnings.filter(
                created_at__date__gte=week_start,
                created_at__date__lte=week_end,
            )
        )
        weekly_data.append({
            'label': week_start.strftime('%b %d'),
            'value': week_earnings,
        })

    # Monthly earnings chart (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if i > 0:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
        else:
            next_month = today + timedelta(days=1)
        month_earnings = sum(
            t.amount for t in earnings.filter(
                created_at__date__gte=month_start,
                created_at__date__lt=next_month,
            )
        )
        monthly_data.append({
            'label': month_start.strftime('%b %Y'),
            'value': month_earnings,
        })

    # Rating trend (reviews over time)
    reviews_list = Review.objects.filter(tutor=request.user).order_by('created_at')
    rating_trend = []
    running_avg = 0
    for idx, r in enumerate(reviews_list, 1):
        running_avg = ((running_avg * (idx - 1)) + r.rating) / idx
        rating_trend.append({
            'label': r.created_at.strftime('%b %d'),
            'value': round(running_avg, 2),
        })

    context = {
        'profile': profile,
        'total_earned': total_earned,
        'monthly_earned': monthly_earned,
        'weekly_earned': weekly_earned,
        'total_students': total_students,
        'total_sessions': total_sessions,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'weekly_chart': json_module.dumps(weekly_data),
        'monthly_chart': json_module.dumps(monthly_data),
        'rating_trend': json_module.dumps(rating_trend),
    }
    return render(request, 'core/earnings_dashboard.html', context)


# ==================== CHATBOT ====================

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def chatbot_api(request):
    """AJAX endpoint for chatbot messages."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        user_message = request.POST.get('message', '').strip()

    if not user_message:
        return JsonResponse({
            'message': "Please type a message!",
            'suggestions': ['Help', 'Find a tutor'],
        })

    from .chatbot import get_chatbot_response
    user = request.user if request.user.is_authenticated else None
    response = get_chatbot_response(user_message, user)

    return JsonResponse(response)

# ==================== ADMIN PANEL ====================
# Import all admin panel views
from .admin_views import (
    admin_panel_view, admin_api_stats, admin_api_users, admin_api_user_action,
    admin_api_skills, admin_api_skill_action, admin_api_sessions,
    admin_api_disputes, admin_api_dispute_action, admin_api_reviews,
    admin_api_send_notification, admin_api_analytics,
    admin_api_reports, admin_api_report_action,
)
