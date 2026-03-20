from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Wallet, Transaction


@receiver(post_save, sender=User)
def create_user_profile_and_wallet(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        wallet, w_created = Wallet.objects.get_or_create(user=instance, defaults={'balance': 100})
        if w_created:
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='signup_bonus',
                amount=100,
                description='Welcome bonus - 100 credits',
                balance_after=100,
            )
