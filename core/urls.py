from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.index, name='index'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('resend-reset-otp/', views.resend_reset_otp_view, name='resend_reset_otp'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Role
    path('switch-role/', views.switch_role, name='switch_role'),

    # Browse
    path('browse-skills/', views.browse_skills_view, name='browse_skills'),

    # Tutor profile
    path('tutor/<int:user_id>/', views.tutor_profile_view, name='tutor_profile'),
    path('edit-profile/', views.edit_tutor_profile_view, name='edit_tutor_profile'),
    path('my-profile/', views.learner_profile_view, name='learner_profile'),

    # Sessions
    path('my-sessions/', views.my_sessions_view, name='my_sessions'),
    path('create-session/', views.create_session_view, name='create_session'),
    path('tutor-complete/<int:session_id>/', views.tutor_complete_session_view, name='tutor_complete_session'),
    path('learner-complete/<int:booking_id>/', views.learner_complete_session_view, name='learner_complete_session'),
    path('report-issue/<int:booking_id>/', views.report_issue_view, name='report_issue'),
    path('start-session/<int:session_id>/', views.start_session_view, name='start_session'),

    # Booking
    path('book/<int:session_id>/', views.book_session_view, name='book_session'),

    # Reviews
    path('review/<int:session_id>/', views.submit_review_view, name='submit_review'),

    # Wallet & Payments
    path('wallet/', views.wallet_view, name='wallet'),
    path('api/create-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('api/verify-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),

    # Messages
    path('inbox/', views.inbox_view, name='inbox'),
    path('chat/<int:user_id>/', views.chat_view, name='chat'),
    path('contact-admin/', views.contact_admin_view, name='contact_admin'),
    path('send-message/<int:user_id>/', views.send_message_view, name='send_message'),
    path('fetch-messages/<int:user_id>/', views.fetch_messages_view, name='fetch_messages'),
    path('api/unread-count/', views.unread_count_view, name='unread_count'),

    # API
    path('api/switch-role/', views.api_switch_role, name='api_switch_role'),
    path('api/book/<int:session_id>/', views.api_book_session, name='api_book_session'),
    path('api/check-email/', views.api_check_email, name='api_check_email'),
    path('api/register/', views.api_register, name='api_register'),

    # Chatbot
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),

    # Notifications
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/read/<int:notif_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # Tutor Availability
    path('manage-availability/', views.manage_availability_view, name='manage_availability'),

    # Session Materials
    path('upload-material/<int:session_id>/', views.upload_material_view, name='upload_material'),
    path('delete-material/<int:material_id>/', views.delete_material_view, name='delete_material'),

    # Reschedule
    path('reschedule/<int:session_id>/', views.tutor_reschedule_session, name='tutor_reschedule'),
    path('respond-reschedule/<int:booking_id>/', views.learner_respond_reschedule, name='respond_reschedule'),

    # Reports
    path('file-report/<int:booking_id>/', views.file_report_view, name='file_report'),
    path('respond-report/<int:report_id>/', views.tutor_respond_report, name='tutor_respond_report'),

    # Earnings Dashboard
    path('earnings/', views.earnings_dashboard_view, name='earnings_dashboard'),

    # Custom Admin Panel
    path('panel/', views.admin_panel_view, name='admin_panel'),
    path('panel/api/stats/', views.admin_api_stats, name='admin_api_stats'),
    path('panel/api/users/', views.admin_api_users, name='admin_api_users'),
    path('panel/api/user/<int:user_id>/action/', views.admin_api_user_action, name='admin_api_user_action'),
    path('panel/api/skills/', views.admin_api_skills, name='admin_api_skills'),
    path('panel/api/skill/action/', views.admin_api_skill_action, name='admin_api_skill_action'),
    path('panel/api/sessions/', views.admin_api_sessions, name='admin_api_sessions'),
    path('panel/api/disputes/', views.admin_api_disputes, name='admin_api_disputes'),
    path('panel/api/dispute/<int:booking_id>/action/', views.admin_api_dispute_action, name='admin_api_dispute_action'),
    path('panel/api/reviews/', views.admin_api_reviews, name='admin_api_reviews'),
    path('panel/api/notifications/send/', views.admin_api_send_notification, name='admin_api_send_notification'),
    path('panel/api/analytics/', views.admin_api_analytics, name='admin_api_analytics'),
    path('panel/api/reports/', views.admin_api_reports, name='admin_api_reports'),
    path('panel/api/report/<int:report_id>/action/', views.admin_api_report_action, name='admin_api_report_action'),
]
