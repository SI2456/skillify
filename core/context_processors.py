from django.db.models import Q


def unread_messages(request):
    """Make unread message count available in every template."""
    if request.user.is_authenticated:
        from .models import Message
        count = Message.objects.filter(
            Q(conversation__user1=request.user) | Q(conversation__user2=request.user),
            is_read=False
        ).exclude(sender=request.user).count()
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}
