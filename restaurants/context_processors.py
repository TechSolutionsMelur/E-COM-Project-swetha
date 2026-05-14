from orders.models import Order


def restaurant_context(request):
    """
    Injects pending order count into every template
    for verified restaurant owners.
    """
    if (request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'restaurant'):
        try:
            profile = request.user.restaurant_profile
            if profile.is_verified:
                pending = Order.objects.filter(
                    restaurant=profile,
                    status='pending'
                ).count()
                return {'pending_count': pending}
        except Exception:
            pass
    return {'pending_count': 0}