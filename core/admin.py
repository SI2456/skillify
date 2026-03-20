from django.contrib import admin
from .models import (Skill, UserProfile, Session, Booking, Review, Wallet,
                     Transaction, Conversation, Message, Notification,
                     TutorAvailability, SessionMaterial, Payment, SessionReport)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'trust_score', 'is_verified')
    list_filter = ('role', 'is_verified')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'tutor', 'skill', 'date', 'status', 'credits_required', 'has_zoom')
    list_filter = ('status', 'skill')
    readonly_fields = ('zoom_meeting_id', 'zoom_join_url', 'zoom_start_url', 'zoom_password')

    def has_zoom(self, obj):
        return bool(obj.zoom_join_url)
    has_zoom.boolean = True
    has_zoom.short_description = 'Zoom'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('learner', 'session', 'status', 'credits_paid', 'tutor_confirmed', 'learner_confirmed', 'is_disputed', 'booked_at')
    list_filter = ('status', 'is_disputed', 'tutor_confirmed', 'learner_confirmed')
    readonly_fields = ('tutor_confirmed_at', 'learner_confirmed_at', 'dispute_created_at')
    fieldsets = (
        (None, {
            'fields': ('learner', 'session', 'status', 'credits_paid')
        }),
        ('Dual Confirmation', {
            'fields': ('tutor_confirmed', 'tutor_confirmed_at', 'learner_confirmed', 'learner_confirmed_at'),
        }),
        ('Dispute', {
            'fields': ('is_disputed', 'dispute_reason', 'dispute_created_at', 'dispute_resolved'),
            'classes': ('collapse',),
        }),
    )
    actions = ['resolve_dispute_release', 'resolve_dispute_refund']

    def resolve_dispute_release(self, request, queryset):
        """Admin resolves dispute — release credits to tutor."""
        for booking in queryset.filter(is_disputed=True, dispute_resolved=False):
            booking.dispute_resolved = True
            booking.is_disputed = False
            booking.tutor_confirmed = True
            booking.learner_confirmed = True
            booking.check_dual_completion()
            booking.session.status = 'completed'
            booking.session.save()
        self.message_user(request, f'{queryset.count()} dispute(s) resolved — credits released to tutor.')
    resolve_dispute_release.short_description = '✅ Resolve: Release credits to tutor'

    def resolve_dispute_refund(self, request, queryset):
        """Admin resolves dispute — refund credits to learner."""
        for booking in queryset.filter(is_disputed=True, dispute_resolved=False):
            booking.dispute_resolved = True
            booking.status = 'cancelled'
            booking.save()
            # Refund learner
            learner_wallet = booking.learner.wallet
            learner_wallet.balance += booking.credits_paid
            learner_wallet.save()
            from .models import Transaction
            Transaction.objects.create(
                wallet=learner_wallet,
                transaction_type='credit',
                amount=booking.credits_paid,
                description=f'Refund: Dispute resolved for {booking.session.title}',
                balance_after=learner_wallet.balance,
            )
            booking.session.status = 'cancelled'
            booking.session.save()
        self.message_user(request, f'{queryset.count()} dispute(s) resolved — credits refunded to learner.')
    resolve_dispute_refund.short_description = '💰 Resolve: Refund credits to learner'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'tutor', 'rating', 'created_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'updated_at', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'content_short', 'is_read', 'created_at')
    list_filter = ('is_read',)

    def content_short(self, obj):
        return obj.content[:50]
    content_short.short_description = 'Message'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')


@admin.register(TutorAvailability)
class TutorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('tutor', 'day_of_week', 'start_time', 'end_time', 'skill', 'credits_per_session', 'is_active')
    list_filter = ('day_of_week', 'is_active')


@admin.register(SessionMaterial)
class SessionMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'session', 'filename', 'uploaded_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_display', 'credits', 'status', 'razorpay_payment_id', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'paid_at')

    def amount_display(self, obj):
        return f'₹{obj.amount_inr // 100}'
    amount_display.short_description = 'Amount'


@admin.register(SessionReport)
class SessionReportAdmin(admin.ModelAdmin):
    list_display = ('pk', 'report_type', 'reporter', 'tutor', 'verdict', 'auto_score', 'created_at')
    list_filter = ('report_type', 'verdict')
    readonly_fields = ('auto_score', 'flag_no_show', 'flag_short_session', 'flag_no_engagement',
                       'flag_payment_issue', 'flag_repeat_offender')
