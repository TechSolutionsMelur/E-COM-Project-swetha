from .models import Cart


def cart_processor(request):
    """
    Injects cart info into every template context.
    Only runs for authenticated customers.
    """
    if request.user.is_authenticated and \
       hasattr(request.user, 'role') and \
       request.user.role == 'customer':
        try:
            cart = Cart.objects.prefetch_related(
                'items__menu_item'
            ).get(user=request.user)
            return {
                'cart':             cart,
                'cart_total_items': cart.total_items,
                'cart_subtotal':    cart.subtotal,
            }
        except Cart.DoesNotExist:
            pass
    return {
        'cart':             None,
        'cart_total_items': 0,
        'cart_subtotal':    0,
    }