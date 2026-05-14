from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from restaurants.models import RestaurantProfile, MenuItem, MenuCategory
from .models import Cart, CartItem
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from restaurants.models import Offer
from restaurants.models import RestaurantProfile, Offer
from django.db.models import Q, Exists, OuterRef, Sum
from django.utils import timezone
from .models import Cart, CartItem, Order, OrderItem, DeliveryAddress
from .forms  import DeliveryAddressForm, CheckoutForm


#  Guard — customers only
def customer_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to continue.")
            return redirect('login')
        if request.user.role != 'customer':
            return redirect('restaurant_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


#  Helper — get or create cart
def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


#  Customer Dashboard
@login_required
@customer_required
def customer_dashboard(request):
    now = timezone.now()

    featured_restaurants = RestaurantProfile.objects.filter(
        is_verified=True, is_open=True
    ).annotate(
        has_active_offer=Exists(
            Offer.objects.filter(
                restaurant=OuterRef('pk'),
                is_active=True,
            ).filter(
                Q(valid_until__isnull=True) |
                Q(valid_until__gt=now)
            )
        )
    ).order_by('-submitted_at')[:6]

    cart = get_or_create_cart(request.user)

    # Order stats
    user_orders     = Order.objects.filter(user=request.user)
    total_orders    = user_orders.count()
    delivered_orders= user_orders.filter(status='delivered').count()
    unique_restaurants = user_orders.values(
        'restaurant'
    ).distinct().count()
    total_spent     = user_orders.filter(
        status='delivered'
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    recent_orders = user_orders.order_by('-placed_at')[:3]

    return render(request, 'orders/customer_dashboard.html', {
        'featured_restaurants': featured_restaurants,
        'cart':                 cart,
        'total_orders':         total_orders,
        'delivered_orders':     delivered_orders,
        'unique_restaurants':   unique_restaurants,
        'total_spent':          total_spent,
        'recent_orders':        recent_orders,
    })
#  Restaurant Detail / Menu
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(
        RestaurantProfile, pk=pk, is_verified=True
    )
    from django.utils import timezone
    from restaurants.models import Offer
    from django.db.models import Q
    now = timezone.now()

    active_offers = Offer.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gt=now)
    )

    categories    = MenuCategory.objects.filter(
        restaurant=restaurant
    ).prefetch_related('items')
    uncategorized = MenuItem.objects.filter(
        restaurant=restaurant,
        menu_category=None,
        is_available=True
    )
    cart_item_map = {}
    if request.user.is_authenticated and \
       request.user.role == 'customer':
        cart = get_or_create_cart(request.user)
        if cart.restaurant == restaurant:
            for ci in cart.items.select_related('menu_item').all():
                cart_item_map[ci.menu_item.id] = ci.quantity

    return render(request, 'orders/restaurant_details.html', {
        'restaurant':    restaurant,
        'categories':    categories,
        'uncategorized': uncategorized,
        'cart_item_map': cart_item_map,
        'active_offers': active_offers,
    })
#  Add to Cart
@login_required
@customer_required
@require_POST
def add_to_cart(request, item_id):
    menu_item  = get_object_or_404(MenuItem, pk=item_id, is_available=True)
    cart       = get_or_create_cart(request.user)
    restaurant = menu_item.restaurant

    # If cart has items from a different restaurant — ask user
    if cart.restaurant and cart.restaurant != restaurant:
        if request.POST.get('confirm_clear') == 'yes':
            cart.clear()
        else:
            return JsonResponse({
                'status':      'conflict',
                'message':     (
                    f'Your cart has items from '
                    f'<strong>{cart.restaurant.restaurant_name}</strong>. '
                    f'Clear cart and add from '
                    f'<strong>{restaurant.restaurant_name}</strong>?'
                ),
                'item_id':     item_id,
            })

    # Set restaurant on cart
    cart.restaurant = restaurant
    cart.save()

    # Add or increment
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        menu_item=menu_item,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return JsonResponse({
        'status':      'ok',
        'message':     f"'{menu_item.name}' added to cart.",
        'cart_count':  cart.total_items,
        'item_qty':    cart_item.quantity,
        'item_total':  str(cart_item.item_total),
        'cart_subtotal': str(cart.subtotal),
    })


#  Remove from Cart
@login_required
@customer_required
@require_POST
def remove_from_cart(request, item_id):
    cart      = get_or_create_cart(request.user)
    menu_item = get_object_or_404(MenuItem, pk=item_id)

    try:
        cart_item = CartItem.objects.get(cart=cart, menu_item=menu_item)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            qty = cart_item.quantity
        else:
            cart_item.delete()
            qty = 0

        # If cart is now empty, clear restaurant
        if cart.items.count() == 0:
            cart.restaurant = None
            cart.save()

        return JsonResponse({
            'status':        'ok',
            'item_qty':      qty,
            'item_total':    str(
                menu_item.price * qty if qty > 0 else 0
            ),
            'cart_count':    cart.total_items,
            'cart_subtotal': str(cart.subtotal),
        })
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'not_found'}, status=404)


#  Delete Item Entirely from Cart
@login_required
@customer_required
@require_POST
def delete_from_cart(request, item_id):
    cart      = get_or_create_cart(request.user)
    menu_item = get_object_or_404(MenuItem, pk=item_id)

    CartItem.objects.filter(cart=cart, menu_item=menu_item).delete()

    if cart.items.count() == 0:
        cart.restaurant = None
        cart.save()

    return JsonResponse({
        'status':        'ok',
        'cart_count':    cart.total_items,
        'cart_subtotal': str(cart.subtotal),
    })


#  Cart Page
@login_required
@customer_required
def cart_detail(request):
    cart = get_or_create_cart(request.user)
    cart_items = cart.items.select_related(
        'menu_item', 'menu_item__restaurant'
    ).all()

    # Delivery fee logic (simple flat rate)
    delivery_fee = 0
    if not cart.is_empty and cart.restaurant:
        delivery_fee = 40  # ₹40 flat — can be dynamic later

    taxes   = round(float(cart.subtotal) * 0.05, 2)  # 5% GST
    total   = float(cart.subtotal) + delivery_fee + taxes

    return render(request, 'orders/cart.html', {
        'cart':         cart,
        'cart_items':   cart_items,
        'delivery_fee': delivery_fee,
        'taxes':        taxes,
        'total':        total,
    })


#  Clear Cart
@login_required
@customer_required
@require_POST
def clear_cart(request):
    cart = get_or_create_cart(request.user)
    cart.clear()
    messages.info(request, "Cart cleared.")
    return redirect('cart_detail')

#  Checkout — Step 1: Address
@login_required
@customer_required
def checkout(request):
    cart = get_or_create_cart(request.user)

    if cart.is_empty:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart_detail')

    # Min order check
    if cart.restaurant and cart.subtotal < cart.restaurant.min_order_amount:
        messages.warning(
            request,
            f"Minimum order for {cart.restaurant.restaurant_name} "
            f"is ₹{cart.restaurant.min_order_amount}."
        )
        return redirect('cart_detail')

    saved_addresses = DeliveryAddress.objects.filter(user=request.user)
    address_form    = DeliveryAddressForm(request.POST or None)

    if request.method == 'POST':
        selected_id = request.POST.get('selected_address')

        if selected_id:
            # Using a saved address
            address = get_object_or_404(
                DeliveryAddress, pk=selected_id, user=request.user
            )
            request.session['checkout_address_id'] = address.pk
            return redirect('checkout_payment')

        elif address_form.is_valid():
            # Saving a new address
            address         = address_form.save(commit=False)
            address.user    = request.user
            address.save()
            request.session['checkout_address_id'] = address.pk
            messages.success(request, "Address saved.")
            return redirect('checkout_payment')

    return render(request, 'orders/checkout/step1_address.html', {
        'cart':             cart,
        'saved_addresses':  saved_addresses,
        'address_form':     address_form,
        'step':             1,
    })


#  Checkout — Step 2: Payment
@login_required
@customer_required
def checkout_payment(request):
    cart       = get_or_create_cart(request.user)
    address_id = request.session.get('checkout_address_id')

    if cart.is_empty or not address_id:
        return redirect('checkout')

    address      = get_object_or_404(
        DeliveryAddress, pk=address_id, user=request.user
    )
    delivery_fee = Decimal('40.00')
    taxes        = (cart.subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
    total        = cart.subtotal + delivery_fee + taxes

    form = CheckoutForm(request.POST or None,
                        initial={'payment_method': 'cod'})

    if request.method == 'POST' and form.is_valid():
        payment_method       = form.cleaned_data['payment_method']
        special_instructions = form.cleaned_data['special_instructions']

        # ── Create Order ──
        order = Order.objects.create(
            user            = request.user,
            restaurant      = cart.restaurant,
            # Address snapshot
            delivery_name   = address.full_name,
            delivery_phone  = address.phone,
            delivery_address= address.full_address,
            delivery_city   = address.city,
            delivery_pincode= address.pincode,
            # Financials
            subtotal        = cart.subtotal,
            delivery_fee    = delivery_fee,
            taxes           = taxes,
            total_amount    = total,
            # Payment
            payment_method  = payment_method,
            is_paid         = payment_method != 'cod',
            paid_at         = timezone.now() if payment_method != 'cod'
                              else None,
            # Notes
            special_instructions = special_instructions,
            # ETA
            estimated_delivery = timezone.now() + timedelta(
                minutes=cart.restaurant.avg_delivery_time
            ),
        )

        # ── Snapshot order items ──
        for ci in cart.items.select_related('menu_item').all():
            OrderItem.objects.create(
                order      = order,
                menu_item  = ci.menu_item,
                item_name  = ci.menu_item.name,
                item_price = ci.menu_item.price,
                item_type  = ci.menu_item.item_type,
                quantity   = ci.quantity,
            )

        # ── Increment restaurant order count ──
        if cart.restaurant:
            cart.restaurant.total_orders += 1
            cart.restaurant.save(update_fields=['total_orders'])

        # ── Clear cart ──
        cart.clear()

        # ── Clear session ──
        request.session.pop('checkout_address_id', None)

        messages.success(
            request,
            f"Order #{order.order_number} placed successfully! 🎉"
        )
        return redirect('order_success', order_number=order.order_number)

    return render(request, 'orders/checkout/step2_payment.html', {
        'cart':         cart,
        'address':      address,
        'form':         form,
        'delivery_fee': delivery_fee,
        'taxes':        taxes,
        'total':        total,
        'step':         2,
    })


#  Order Success

@login_required
def order_success(request, order_number):
    order = get_object_or_404(
        Order, order_number=order_number, user=request.user
    )
    return render(request, 'orders/order_success.html', {
        'order': order
    })


#  Order History
@login_required
@customer_required
def order_history(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items').order_by('-placed_at')

    return render(request, 'orders/order_history.html', {
        'orders': orders
    })


#  Order Detail
@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order, order_number=order_number, user=request.user
    )
    return render(request, 'orders/order_detail.html', {
        'order': order
    })


#  Cancel Order
@login_required
@customer_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(
        Order, order_number=order_number, user=request.user
    )
    if order.can_cancel:
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        messages.success(
            request,
            f"Order #{order.order_number} has been cancelled."
        )
    else:
        messages.error(
            request,
            "This order can no longer be cancelled."
        )
    return redirect('order_detail', order_number=order.order_number)


@login_required
@customer_required
def apply_coupon(request):
    """AJAX endpoint — applies promo code to cart."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)

    code = request.POST.get('code', '').strip().upper()
    cart = get_or_create_cart(request.user)

    if cart.is_empty:
        return JsonResponse({
            'status':  'error',
            'message': 'Your cart is empty.'
        })

    try:
        offer = Offer.objects.get(
            code=code,
            restaurant=cart.restaurant,
            is_active=True
        )
    except Offer.DoesNotExist:
        return JsonResponse({
            'status':  'error',
            'message': f"Code '{code}' is not valid for this restaurant."
        })

    if not offer.is_valid:
        return JsonResponse({
            'status':  'error',
            'message': 'This offer has expired or reached its usage limit.'
        })

    if cart.subtotal < offer.min_order_value:
        return JsonResponse({
            'status':  'error',
            'message': (
                f"Minimum order of ₹{offer.min_order_value} "
                f"required for this offer."
            )
        })

    discount = Decimal(str(offer.calculate_discount(cart.subtotal)))
    cart.applied_offer   = offer
    cart.discount_amount = discount
    cart.save()

    return JsonResponse({
        'status':          'ok',
        'message':         f"🎉 Offer applied! You saved ₹{discount}",
        'discount':        str(discount),
        'discounted_total':str(cart.discounted_total),
        'offer_title':     offer.title,
    })


@login_required
@customer_required
@require_POST
def remove_coupon(request):
    cart                 = get_or_create_cart(request.user)
    cart.applied_offer   = None
    cart.discount_amount = 0
    cart.save()
    return JsonResponse({
        'status':   'ok',
        'message':  'Offer removed.',
        'subtotal': str(cart.subtotal),
    })

#search view   

def customer_search(request):
    """Search both restaurants and dishes."""
    from restaurants.models import RestaurantProfile, MenuItem, Offer
    from django.db.models import Q, Exists, OuterRef
    from django.utils import timezone

    query = request.GET.get('q', '').strip()
    now   = timezone.now()

    restaurants = []
    dishes      = []

    if query:
        # Search restaurants
        restaurants = RestaurantProfile.objects.filter(
            is_verified=True
        ).filter(
            Q(restaurant_name__icontains=query) |
            Q(cuisine_type__icontains=query)    |
            Q(city__icontains=query)            |
            Q(description__icontains=query)
        ).annotate(
            has_active_offer=Exists(
                Offer.objects.filter(
                    restaurant=OuterRef('pk'),
                    is_active=True,
                ).filter(
                    Q(valid_until__isnull=True) |
                    Q(valid_until__gt=now)
                )
            )
        )

        # Search dishes
        dishes = MenuItem.objects.filter(
            is_available=True,
            restaurant__is_verified=True
        ).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).select_related('restaurant')[:20]

    return render(request, 'orders/search_results.html', {
        'query':        query,
        'restaurants':  restaurants,
        'dishes':       dishes,
        'rest_count':   len(restaurants),
        'dish_count':   len(dishes),
    })