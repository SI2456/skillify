from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from django.contrib.auth.models import User


class SkillifyAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        """If email already exists, connect Google to that account automatically."""
        email = sociallogin.account.extra_data.get('email', '').lower()
        if not email:
            return

        try:
            user = User.objects.get(email=email)
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
