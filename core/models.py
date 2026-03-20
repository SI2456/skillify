from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='bi-lightbulb')

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('learner', 'Learner'),
        ('tutor', 'Tutor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='learner')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    expertise = models.CharField(max_length=255, blank=True, default='')
    demo_video = models.URLField(blank=True, default='', help_text='YouTube, Vimeo, or Google Drive link')
    linkedin = models.URLField(blank=True, default='')
    github = models.URLField(blank=True, default='')
    skills = models.ManyToManyField(Skill, blank=True, related_name='users')
    trust_score = models.FloatField(default=0.0)
    otp = models.CharField(max_length=6, blank=True, default='')
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    # Experience & Education
    experience_years = models.PositiveIntegerField(default=0, help_text='Years of experience')
    education = models.TextField(blank=True, default='', help_text='Education details')
    show_experience = models.BooleanField(default=True, help_text='Show experience on public profile')
    show_education = models.BooleanField(default=True, help_text='Show education on public profile')

    # Tutor certificates
    certificate = models.FileField(upload_to='certificates/', blank=True, null=True, help_text='Teaching certificate PDF/image')
    certificate_title = models.CharField(max_length=255, blank=True, default='', help_text='e.g. B.Ed, TESOL, AWS Certified')

    # Learner profile fields
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    learning_interests = models.TextField(blank=True, default='', help_text='What topics are you interested in?')
    skill_level = models.CharField(max_length=15, choices=LEVEL_CHOICES, blank=True, default='beginner')

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def avatar_url(self):
        """Return uploaded profile picture URL or fallback to generated avatar."""
        if self.profile_picture:
            return self.profile_picture.url
        name = self.user.get_full_name() or self.user.username
        name_encoded = name.replace(' ', '+')
        colors = ['4ECDC4', '667eea', 'f093fb', '4facfe', 'FFB84D', 'f5576c']
        color = colors[self.user.pk % len(colors)]
        return f"https://ui-avatars.com/api/?name={name_encoded}&background={color}&color=fff&size=150"

    def average_rating(self):
        """Return average star rating from reviews (1-5 scale)."""
        from django.db.models import Avg
        avg = self.user.reviews_received.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 1) if avg else 0

    def review_count(self):
        """Return total number of reviews."""
        return self.user.reviews_received.count()

    def sessions_completed_count(self):
        """Return total completed sessions taught."""
        from .models import Session
        return Session.objects.filter(tutor=self.user, status='completed').count()

    def calculate_trust_score(self):
        """
        Trust Score Formula (out of 100):
        - Avg Rating: 60% weight (max 60 pts from 5-star avg)
        - Sessions Completed: 25% weight (2 pts each, max 25)
        - Review Count: 15% weight (1.5 pts each, max 15)
        """
        avg = self.average_rating()
        sessions = self.sessions_completed_count()
        reviews = self.review_count()

        rating_score = min((avg / 5) * 60, 60) if avg else 0
        session_score = min(sessions * 2, 25)
        review_score = min(reviews * 1.5, 15)

        return round(min(rating_score + session_score + review_score, 100), 1)

    def get_embed_video_url(self):
        """Convert YouTube/Vimeo/Google Drive URL to embeddable iframe URL."""
        url = self.demo_video
        if not url:
            return ''
        # YouTube formats
        if 'youtube.com/watch' in url:
            import re
            match = re.search(r'v=([a-zA-Z0-9_-]+)', url)
            if match:
                return f'https://www.youtube.com/embed/{match.group(1)}'
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            return f'https://www.youtube.com/embed/{video_id}'
        elif 'youtube.com/embed/' in url:
            return url
        # Vimeo formats
        elif 'vimeo.com/' in url:
            import re
            match = re.search(r'vimeo\.com/(\d+)', url)
            if match:
                return f'https://player.vimeo.com/video/{match.group(1)}'
        # Google Drive formats
        elif 'drive.google.com' in url:
            import re
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
            if match:
                return f'https://drive.google.com/file/d/{match.group(1)}/preview'
        return url


class Session(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all', 'All Levels'),
    ]

    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutor_sessions')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='sessions')
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default='all')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    credits_required = models.IntegerField(default=50)
    session_type = models.CharField(max_length=20, default='one-to-one')
    max_participants = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)

    # Zoom Integration
    zoom_meeting_id = models.CharField(max_length=50, blank=True, default='')
    zoom_join_url = models.URLField(max_length=500, blank=True, default='')
    zoom_start_url = models.URLField(max_length=1000, blank=True, default='')
    zoom_password = models.CharField(max_length=20, blank=True, default='')

    def __str__(self):
        return f"{self.title} by {self.tutor.get_full_name()}"

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0


class SessionMaterial(models.Model):
    """Files/PDFs uploaded by tutor for a session."""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='session_materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.session.title}"

    def filename(self):
        import os
        return os.path.basename(self.file.name)


class TutorAvailability(models.Model):
    """Weekly recurring availability for tutors."""
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='availability_slots')
    credits_per_session = models.IntegerField(default=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name_plural = 'Tutor Availabilities'

    def __str__(self):
        return f"{self.tutor.get_full_name()} — {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class Notification(models.Model):
    """In-app notifications for users."""
    TYPE_CHOICES = [
        ('booking_new', 'New Booking'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('session_reminder', 'Session Reminder'),
        ('session_started', 'Session Started'),
        ('review_received', 'Review Received'),
        ('credits_received', 'Credits Received'),
        ('credits_refunded', 'Credits Refunded'),
        ('message_new', 'New Message'),
        ('dispute_opened', 'Dispute Opened'),
        ('dispute_resolved', 'Dispute Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.first_name}: {self.title}"

    @staticmethod
    def create_notification(user, ntype, title, message, link=''):
        return Notification.objects.create(
            user=user, notification_type=ntype,
            title=title, message=message, link=link,
        )


class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('tutor_completed', 'Tutor Completed'),
        ('learner_completed', 'Learner Completed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('pending_review', 'Pending Review'),
        ('disputed', 'Disputed'),
    ]

    learner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    booked_at = models.DateTimeField(auto_now_add=True)
    credits_paid = models.IntegerField(default=0)

    # Dual confirmation
    tutor_confirmed = models.BooleanField(default=False)
    learner_confirmed = models.BooleanField(default=False)
    tutor_confirmed_at = models.DateTimeField(null=True, blank=True)
    learner_confirmed_at = models.DateTimeField(null=True, blank=True)

    # Dispute
    is_disputed = models.BooleanField(default=False)
    dispute_reason = models.TextField(blank=True, default='')
    dispute_created_at = models.DateTimeField(null=True, blank=True)
    dispute_resolved = models.BooleanField(default=False)

    # Reschedule
    RESCHEDULE_CHOICES = [
        ('none', 'No Reschedule'),
        ('pending', 'Pending Learner Response'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('auto_rejected', 'Auto-Rejected (Timeout)'),
    ]
    reschedule_status = models.CharField(max_length=15, choices=RESCHEDULE_CHOICES, default='none')
    reschedule_new_date = models.DateField(null=True, blank=True)
    reschedule_new_start = models.TimeField(null=True, blank=True)
    reschedule_new_end = models.TimeField(null=True, blank=True)
    reschedule_reason = models.TextField(blank=True, default='')
    reschedule_requested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('learner', 'session')

    def __str__(self):
        return f"{self.learner.username} -> {self.session.title}"

    def check_dual_completion(self):
        """Check if both confirmed. If yes, release credits."""
        if self.tutor_confirmed and self.learner_confirmed and not self.is_disputed:
            self._release_credits()
            return True
        return False

    def _release_credits(self):
        """Transfer credits to tutor wallet."""
        if self.status in ('completed', 'pending_review'):
            return
        tutor_wallet = self.session.tutor.wallet
        tutor_wallet.balance += self.credits_paid
        tutor_wallet.save()
        Transaction.objects.create(
            wallet=tutor_wallet,
            transaction_type='tutor_earning',
            amount=self.credits_paid,
            description=f'Earned from: {self.session.title}',
            balance_after=tutor_wallet.balance,
        )
        self.status = 'pending_review'
        self.save()


class Review(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'reviewer')

    def __str__(self):
        return f"Review by {self.reviewer.username} - {self.rating}/5"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=100)

    def __str__(self):
        return f"{self.user.username}'s Wallet: {self.balance} credits"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('signup_bonus', 'Signup Bonus'),
        ('booking_payment', 'Booking Payment'),
        ('tutor_earning', 'Tutor Earning'),
        ('razorpay_topup', 'Razorpay Top-Up'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.IntegerField()
    description = models.CharField(max_length=255)
    balance_after = models.IntegerField()
    payment_id = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} credits"


class Payment(models.Model):
    """Razorpay payment records."""
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default='')
    razorpay_signature = models.CharField(max_length=255, blank=True, default='')
    amount_inr = models.IntegerField(help_text='Amount in INR (paise)')
    credits = models.IntegerField(help_text='Credits to add')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"₹{self.amount_inr // 100} → {self.credits} credits ({self.status})"


class Conversation(models.Model):
    """A conversation thread between two users."""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_user2')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1.get_full_name()} ↔ {self.user2.get_full_name()}"

    def other_user(self, current_user):
        """Return the other participant."""
        return self.user2 if self.user1 == current_user else self.user1

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    @staticmethod
    def get_or_create_conversation(user_a, user_b):
        """Get existing conversation or create one. Ensures user1.pk < user2.pk for uniqueness."""
        if user_a.pk == user_b.pk:
            return None
        u1, u2 = (user_a, user_b) if user_a.pk < user_b.pk else (user_b, user_a)
        conv, _ = Conversation.objects.get_or_create(user1=u1, user2=u2)
        return conv


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.first_name}: {self.content[:40]}"

    def attachment_filename(self):
        if self.attachment:
            import os
            return os.path.basename(self.attachment.name)
        return ''

    def is_image(self):
        if self.attachment:
            return self.attachment.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        return False


class SessionReport(models.Model):
    """Advanced report system with auto-verification."""
    REPORT_TYPE_CHOICES = [
        ('no_show', 'Tutor No-Show'),
        ('incomplete', 'Incomplete Session'),
        ('poor_quality', 'Poor Quality Teaching'),
        ('inappropriate', 'Inappropriate Behavior'),
        ('technical', 'Technical Issues'),
        ('fraud', 'Payment Fraud'),
        ('other', 'Other'),
    ]
    VERDICT_CHOICES = [
        ('pending', 'Pending Analysis'),
        ('likely_valid', 'Likely Valid'),
        ('likely_invalid', 'Likely Invalid'),
        ('needs_review', 'Needs Review'),
        ('valid', 'Valid — Resolved'),
        ('invalid', 'Invalid — Dismissed'),
        ('tutor_response_pending', 'Awaiting Tutor Response'),
    ]

    # Core
    booking = models.OneToOneField('Booking', on_delete=models.CASCADE, related_name='report')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_reports')
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_against')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    description = models.TextField()
    evidence_link = models.URLField(blank=True, default='', help_text='Link to screenshot/video evidence')
    evidence_file = models.FileField(upload_to='report_evidence/', blank=True, null=True)

    # Session tracking data (auto-captured)
    session_date = models.DateField()
    session_scheduled_start = models.TimeField()
    session_scheduled_end = models.TimeField()
    session_actual_duration = models.IntegerField(default=0, help_text='Actual duration in minutes')
    tutor_joined = models.BooleanField(default=False)
    tutor_join_time = models.DateTimeField(null=True, blank=True)
    chat_message_count = models.IntegerField(default=0)
    learner_message_count = models.IntegerField(default=0)
    tutor_message_count = models.IntegerField(default=0)
    payment_status = models.CharField(max_length=20, default='paid')
    has_zoom_meeting = models.BooleanField(default=False)

    # Auto-verification flags
    flag_no_show = models.BooleanField(default=False, help_text='Tutor never started/joined')
    flag_short_session = models.BooleanField(default=False, help_text='Session was < 50% of scheduled duration')
    flag_no_engagement = models.BooleanField(default=False, help_text='Very few messages exchanged')
    flag_payment_issue = models.BooleanField(default=False, help_text='Payment anomaly detected')
    flag_repeat_offender = models.BooleanField(default=False, help_text='Tutor has multiple past reports')
    auto_score = models.IntegerField(default=0, help_text='0-100 validity score from auto-check')

    # System verdict
    verdict = models.CharField(max_length=25, choices=VERDICT_CHOICES, default='pending')
    verdict_reason = models.TextField(blank=True, default='')

    # Tutor response
    tutor_response = models.TextField(blank=True, default='')
    tutor_evidence_file = models.FileField(upload_to='report_tutor_evidence/', blank=True, null=True)
    tutor_responded_at = models.DateTimeField(null=True, blank=True)

    # Admin resolution
    admin_notes = models.TextField(blank=True, default='')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.pk}: {self.get_report_type_display()} — {self.get_verdict_display()}"

    def run_auto_verification(self):
        """Run automated checks and generate a validity score + flags."""
        score = 50  # Start neutral
        session = self.booking.session

        # 1. No-show detection
        if not session.zoom_meeting_id and not self.tutor_joined:
            self.flag_no_show = True
            score += 25

        # 2. Duration check (if session was < 50% of scheduled)
        from datetime import datetime, timedelta
        scheduled_mins = (datetime.combine(datetime.today(), session.end_time) -
                         datetime.combine(datetime.today(), session.start_time)).total_seconds() / 60
        if self.session_actual_duration < scheduled_mins * 0.5 and scheduled_mins > 0:
            self.flag_short_session = True
            score += 15

        # 3. Engagement check
        if self.chat_message_count < 3:
            self.flag_no_engagement = True
            score += 10

        # 4. Payment anomaly
        if self.booking.credits_paid <= 0:
            self.flag_payment_issue = True
            score += 10

        # 5. Repeat offender
        past_valid_reports = SessionReport.objects.filter(
            tutor=self.tutor, verdict='valid'
        ).exclude(pk=self.pk).count()
        if past_valid_reports >= 2:
            self.flag_repeat_offender = True
            score += 15

        # 6. Report type weight
        if self.report_type in ('no_show', 'fraud'):
            score += 10
        elif self.report_type in ('inappropriate',):
            score += 5

        # Cap score
        self.auto_score = min(score, 100)

        # Determine verdict
        if self.auto_score >= 75:
            self.verdict = 'likely_valid'
            self.verdict_reason = 'High confidence: Multiple flags triggered.'
        elif self.auto_score <= 35:
            self.verdict = 'likely_invalid'
            self.verdict_reason = 'Low confidence: Few indicators of issue.'
        else:
            self.verdict = 'needs_review'
            self.verdict_reason = 'Mixed signals: Admin review recommended.'

        self.save()
        return self.verdict

    def tutor_past_stats(self):
        """Get tutor history for admin review."""
        from django.db.models import Avg
        total_reports = SessionReport.objects.filter(tutor=self.tutor).count()
        valid_reports = SessionReport.objects.filter(tutor=self.tutor, verdict='valid').count()
        avg_rating = Review.objects.filter(tutor=self.tutor).aggregate(avg=Avg('rating'))['avg'] or 0
        total_sessions = Session.objects.filter(tutor=self.tutor, status='completed').count()
        return {
            'total_reports': total_reports,
            'valid_reports': valid_reports,
            'avg_rating': round(avg_rating, 1),
            'total_sessions': total_sessions,
            'trust_score': self.tutor.profile.trust_score,
        }
