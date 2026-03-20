"""
Skillify Test Suite
Run: python manage.py test core
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time, timedelta
from core.models import (
    Skill, UserProfile, Session, Booking, Review, Wallet, Transaction,
    Notification, SessionReport, Payment
)


class ModelTests(TestCase):
    """Test model creation and methods."""

    def setUp(self):
        self.skill = Skill.objects.create(name='Python', icon='bi-code-slash')
        self.tutor_user = User.objects.create_user(
            username='tutor@test.com', email='tutor@test.com',
            password='test123', first_name='Test', last_name='Tutor'
        )
        self.learner_user = User.objects.create_user(
            username='learner@test.com', email='learner@test.com',
            password='test123', first_name='Test', last_name='Learner'
        )
        # Profiles and wallets auto-created via signals
        self.tutor_user.profile.role = 'tutor'
        self.tutor_user.profile.save()

        self.session = Session.objects.create(
            tutor=self.tutor_user, title='Python Basics',
            skill=self.skill, level='beginner',
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0),
            credits_required=50, session_type='one-to-one', max_participants=1,
        )

    def test_user_profile_auto_created(self):
        """Signal should auto-create UserProfile and Wallet."""
        self.assertTrue(hasattr(self.tutor_user, 'profile'))
        self.assertTrue(hasattr(self.tutor_user, 'wallet'))
        self.assertEqual(self.tutor_user.wallet.balance, 100)  # signup bonus

    def test_avatar_url_fallback(self):
        """Avatar should return ui-avatars.com URL when no picture uploaded."""
        url = self.tutor_user.profile.avatar_url()
        self.assertIn('ui-avatars.com', url)
        self.assertIn('Test', url)

    def test_trust_score_calculation(self):
        """Trust score should calculate from rating + sessions + reviews."""
        # No reviews = 0 trust
        score = self.tutor_user.profile.calculate_trust_score()
        self.assertEqual(score, 0)

        # Add a review
        booking = Booking.objects.create(
            learner=self.learner_user, session=self.session,
            status='completed', credits_paid=50,
        )
        Review.objects.create(
            session=self.session, reviewer=self.learner_user,
            tutor=self.tutor_user, rating=5, comment='Great!'
        )
        score = self.tutor_user.profile.calculate_trust_score()
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_session_creation(self):
        """Session should be created with correct attributes."""
        self.assertEqual(self.session.title, 'Python Basics')
        self.assertEqual(self.session.level, 'beginner')
        self.assertEqual(self.session.status, 'upcoming')

    def test_booking_creates_correctly(self):
        """Booking should link learner to session."""
        booking = Booking.objects.create(
            learner=self.learner_user, session=self.session,
            status='confirmed', credits_paid=50,
        )
        self.assertEqual(booking.session.tutor, self.tutor_user)
        self.assertEqual(booking.learner, self.learner_user)

    def test_dual_confirmation_releases_credits(self):
        """Credits should transfer when both parties confirm."""
        booking = Booking.objects.create(
            learner=self.learner_user, session=self.session,
            status='confirmed', credits_paid=50,
        )
        tutor_wallet = self.tutor_user.wallet
        initial_balance = tutor_wallet.balance

        booking.tutor_confirmed = True
        booking.learner_confirmed = True
        booking.check_dual_completion()

        tutor_wallet.refresh_from_db()
        self.assertEqual(tutor_wallet.balance, initial_balance + 50)

    def test_notification_creation(self):
        """Notification.create_notification should work."""
        notif = Notification.create_notification(
            self.learner_user, 'booking_confirmed',
            'Test Title', 'Test Message', '/test/'
        )
        self.assertEqual(notif.user, self.learner_user)
        self.assertFalse(notif.is_read)

    def test_google_drive_embed_url(self):
        """Google Drive URLs should convert to preview embeds."""
        self.tutor_user.profile.demo_video = 'https://drive.google.com/file/d/abc123xyz/view'
        url = self.tutor_user.profile.get_embed_video_url()
        self.assertEqual(url, 'https://drive.google.com/file/d/abc123xyz/preview')

    def test_youtube_embed_url(self):
        """YouTube URLs should convert to embed."""
        self.tutor_user.profile.demo_video = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        url = self.tutor_user.profile.get_embed_video_url()
        self.assertIn('/embed/dQw4w9WgXcQ', url)


class ViewTests(TestCase):
    """Test view access and responses."""

    def setUp(self):
        self.client = Client()
        self.learner = User.objects.create_user(
            username='learner@test.com', email='learner@test.com',
            password='test123', first_name='Test', last_name='Learner'
        )
        self.tutor = User.objects.create_user(
            username='tutor@test.com', email='tutor@test.com',
            password='test123', first_name='Test', last_name='Tutor'
        )
        self.tutor.profile.role = 'tutor'
        self.tutor.profile.save()
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='admin123'
        )

    def test_homepage_loads(self):
        """Homepage should return 200."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        """Login page should return 200."""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        """Register page should return 200."""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        """Dashboard should redirect to login if not authenticated."""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_dashboard_loads_for_learner(self):
        """Dashboard should load for logged-in learner."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_browse_skills_learner_only(self):
        """Browse skills should work for learners, redirect tutors."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/browse-skills/')
        self.assertEqual(response.status_code, 200)

        self.client.login(username='tutor@test.com', password='test123')
        response = self.client.get('/browse-skills/')
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard

    def test_wallet_loads(self):
        """Wallet page should load with filters."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/wallet/')
        self.assertEqual(response.status_code, 200)

        # With filters
        response = self.client.get('/wallet/?period=week&type=credit')
        self.assertEqual(response.status_code, 200)

    def test_admin_panel_requires_staff(self):
        """Admin panel should only be accessible to staff users."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)  # Redirect

        self.client.login(username='admin', password='admin123')
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)

    def test_notifications_api(self):
        """Notifications API should return JSON."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('notifications', data)
        self.assertIn('unread_count', data)

    def test_learner_profile_loads(self):
        """Learner profile should load."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/my-profile/')
        self.assertEqual(response.status_code, 200)

    def test_contact_admin(self):
        """Contact admin should create conversation and redirect to chat."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/contact-admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/chat/', response.url)


class BookingFlowTests(TestCase):
    """Test the complete booking flow."""

    def setUp(self):
        self.client = Client()
        self.skill = Skill.objects.create(name='Python')
        self.tutor = User.objects.create_user(
            username='tutor@test.com', email='tutor@test.com',
            password='test123', first_name='Tutor', last_name='User'
        )
        self.tutor.profile.role = 'tutor'
        self.tutor.profile.save()
        self.learner = User.objects.create_user(
            username='learner@test.com', email='learner@test.com',
            password='test123', first_name='Learner', last_name='User'
        )
        self.session = Session.objects.create(
            tutor=self.tutor, title='Python 101', skill=self.skill,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0),
            credits_required=50, max_participants=1,
        )

    def test_booking_deducts_credits(self):
        """Booking should deduct credits from learner wallet."""
        self.client.login(username='learner@test.com', password='test123')
        wallet = self.learner.wallet
        initial = wallet.balance

        response = self.client.post(
            f'/book/{self.session.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, initial - 50)

    def test_cannot_book_own_session(self):
        """Tutor should not be able to book their own session."""
        self.client.login(username='tutor@test.com', password='test123')
        response = self.client.post(
            f'/book/{self.session.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = response.json()
        self.assertFalse(data['success'])

    def test_session_full_blocks_booking(self):
        """One-to-one session should block when already booked."""
        # First booking
        Booking.objects.create(
            learner=self.learner, session=self.session,
            status='confirmed', credits_paid=50,
        )
        # Second learner tries
        learner2 = User.objects.create_user(
            username='learner2@test.com', password='test123'
        )
        self.client.login(username='learner2@test.com', password='test123')
        response = self.client.post(
            f'/book/{self.session.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = response.json()
        self.assertFalse(data['success'])
        self.assertTrue(data.get('session_full', False))

    def test_insufficient_credits(self):
        """Should fail if learner doesn't have enough credits."""
        self.learner.wallet.balance = 10
        self.learner.wallet.save()
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.post(
            f'/book/{self.session.pk}/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = response.json()
        self.assertFalse(data['success'])
        self.assertTrue(data.get('insufficient_credits', False))


class ReportTests(TestCase):
    """Test the report auto-verification system."""

    def setUp(self):
        self.skill = Skill.objects.create(name='Python')
        self.tutor = User.objects.create_user(
            username='tutor@test.com', password='test123',
            first_name='Tutor', last_name='User'
        )
        self.tutor.profile.role = 'tutor'
        self.tutor.profile.save()
        self.learner = User.objects.create_user(
            username='learner@test.com', password='test123'
        )
        self.session = Session.objects.create(
            tutor=self.tutor, title='Test Session', skill=self.skill,
            date=date.today(), start_time=time(10, 0), end_time=time(11, 0),
            credits_required=50, max_participants=1,
        )
        self.booking = Booking.objects.create(
            learner=self.learner, session=self.session,
            status='confirmed', credits_paid=50,
        )

    def test_auto_verification_no_show(self):
        """No-show flag should trigger for sessions without Zoom."""
        report = SessionReport.objects.create(
            booking=self.booking, reporter=self.learner, tutor=self.tutor,
            report_type='no_show', description='Tutor never showed up',
            session_date=self.session.date,
            session_scheduled_start=self.session.start_time,
            session_scheduled_end=self.session.end_time,
            session_actual_duration=0, tutor_joined=False,
            chat_message_count=0, has_zoom_meeting=False,
        )
        verdict = report.run_auto_verification()
        self.assertTrue(report.flag_no_show)
        self.assertGreater(report.auto_score, 50)
        self.assertIn(verdict, ['likely_valid', 'needs_review'])

    def test_auto_verification_low_engagement(self):
        """Low engagement flag should trigger with few messages."""
        report = SessionReport.objects.create(
            booking=self.booking, reporter=self.learner, tutor=self.tutor,
            report_type='poor_quality', description='No interaction',
            session_date=self.session.date,
            session_scheduled_start=self.session.start_time,
            session_scheduled_end=self.session.end_time,
            session_actual_duration=30, tutor_joined=True,
            chat_message_count=1, has_zoom_meeting=True,
        )
        report.run_auto_verification()
        self.assertTrue(report.flag_no_engagement)

    def test_repeat_offender_flag(self):
        """Repeat offender flag should trigger with 2+ valid past reports."""
        # Create 2 past valid reports
        for i in range(2):
            s = Session.objects.create(
                tutor=self.tutor, title=f'Past {i}', skill=self.skill,
                date=date.today() - timedelta(days=i+1),
                start_time=time(10, 0), end_time=time(11, 0), credits_required=50,
            )
            b = Booking.objects.create(learner=self.learner, session=s, credits_paid=50)
            SessionReport.objects.create(
                booking=b, reporter=self.learner, tutor=self.tutor,
                report_type='no_show', description='Past', verdict='valid',
                session_date=s.date, session_scheduled_start=s.start_time,
                session_scheduled_end=s.end_time,
            )

        # New report should flag repeat offender
        report = SessionReport.objects.create(
            booking=self.booking, reporter=self.learner, tutor=self.tutor,
            report_type='no_show', description='Again!',
            session_date=self.session.date,
            session_scheduled_start=self.session.start_time,
            session_scheduled_end=self.session.end_time,
            tutor_joined=False, chat_message_count=0, has_zoom_meeting=False,
        )
        report.run_auto_verification()
        self.assertTrue(report.flag_repeat_offender)


class SecurityTests(TestCase):
    """Test security and access controls."""

    def setUp(self):
        self.client = Client()
        self.learner = User.objects.create_user(
            username='learner@test.com', password='test123'
        )
        self.tutor = User.objects.create_user(
            username='tutor@test.com', password='test123'
        )
        self.tutor.profile.role = 'tutor'
        self.tutor.profile.save()

    def test_unauthenticated_redirects(self):
        """Protected pages should redirect to login."""
        protected = ['/dashboard/', '/wallet/', '/my-sessions/', '/inbox/', '/my-profile/']
        for url in protected:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f'{url} should redirect')

    def test_admin_panel_blocked_for_non_staff(self):
        """Non-staff users should not access admin panel."""
        self.client.login(username='learner@test.com', password='test123')
        response = self.client.get('/panel/')
        self.assertNotEqual(response.status_code, 200)

    def test_tutor_cannot_access_browse_skills(self):
        """Tutors should be redirected from browse skills."""
        self.client.login(username='tutor@test.com', password='test123')
        response = self.client.get('/browse-skills/')
        self.assertEqual(response.status_code, 302)
