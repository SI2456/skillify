from django import template

register = template.Library()


@register.filter
def paise_to_rupees(value):
    """Convert paise (integer) to rupees display string."""
    try:
        return int(value) // 100
    except (ValueError, TypeError):
        return value
