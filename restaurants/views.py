from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from orders.models import Order
from django.views.decorators.http import require_POST
from .models import (
    RestaurantProfile, BankDetails, RestaurantDocument,
    Category, MenuItem, MenuCategory, Offer
)
from .forms import (
    BusinessInfoForm, AddressForm, LegalInfoForm,
    BankDetailsForm, DocumentUploadForm,
    MenuItemForm, MenuCategoryForm,
    RestaurantProfileEditForm, OfferForm,
)
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse



#  Landing Page
def landing_page(request):

    now = timezone.now()

    restaurants = RestaurantProfile.objects.filter(
        is_verified=True
    ).prefetch_related('menu_items', 'documents')

    # ── Search: restaurants AND dishes ──
    query = request.GET.get('q', '').strip()
    dish_results = []

    if query:
        # Filter restaurants by name/cuisine/city/desc
        matched_restaurants = restaurants.filter(
            Q(restaurant_name__icontains=query) |
            Q(cuisine_type__icontains=query)    |
            Q(city__icontains=query)            |
            Q(description__icontains=query)
        )

        # Also find restaurants that have matching dishes
        from .models import MenuItem
        matching_dishes = MenuItem.objects.filter(
            is_available=True,
            restaurant__is_verified=True
        ).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).select_related('restaurant', 'restaurant__menuitem_set')

        # Dish results for display
        dish_results = matching_dishes[:12]

        # Restaurants that serve matching dishes
        dish_restaurant_ids = matching_dishes.values_list(
            'restaurant_id', flat=True
        ).distinct()

        # Merge: restaurants matching by name OR by dish
        restaurants = restaurants.filter(
            Q(id__in=matched_restaurants.values('id')) |
            Q(id__in=dish_restaurant_ids)
        ).distinct()

    # ── Category filter ──
    selected_category = request.GET.get('category', '')
    if selected_category:
        restaurants = restaurants.filter(
            cuisine_type=selected_category
        )

    # ── Open now filter ──
    open_only = request.GET.get('open', '')
    if open_only:
        restaurants = restaurants.filter(is_open=True)

    # ── Has offer filter ──
    has_offer = request.GET.get('offer', '')
    if has_offer:
        restaurants = restaurants.filter(
            offers__is_active=True
        ).filter(
            Q(offers__valid_until__isnull=True) |
            Q(offers__valid_until__gt=now)
        ).distinct()

    # ── Sort ──
    sort = request.GET.get('sort', 'newest')
    sort_map = {
        'newest':    '-submitted_at',
        'delivery':  'avg_delivery_time',
        'min_order': 'min_order_amount',
        'name':      'restaurant_name',
    }
    restaurants = restaurants.order_by(
        sort_map.get(sort, '-submitted_at')
    )

    # ── Annotate has_active_offer ──
    restaurants = restaurants.annotate(
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

    # ── Featured menu items per restaurant for food images ──
    from .models import MenuItem
    featured_items = MenuItem.objects.filter(
        is_available=True,
        restaurant__is_verified=True,
        image__isnull=False,
    ).exclude(image='').select_related('restaurant')

    # Build a dict: restaurant_id -> [items]
    rest_food_images = {}
    for item in featured_items:
        rid = item.restaurant_id
        if rid not in rest_food_images:
            rest_food_images[rid] = []
        if len(rest_food_images[rid]) < 3:
            rest_food_images[rid].append(item)

    categories      = Category.objects.all()
    cuisine_choices = RestaurantProfile.CUISINE_CHOICES

    total_restaurants = RestaurantProfile.objects.filter(
        is_verified=True
    ).count()
    total_cities = RestaurantProfile.objects.filter(
        is_verified=True
    ).values('city').distinct().count()

    context = {
        'restaurants':       restaurants,
        'dish_results':      dish_results,
        'categories':        categories,
        'cuisine_choices':   cuisine_choices,
        'query':             query,
        'selected_category': selected_category,
        'open_only':         open_only,
        'has_offer':         has_offer,
        'sort':              sort,
        'total_restaurants': total_restaurants,
        'total_cities':      total_cities,
        'rest_food_images':  rest_food_images,
    }
    return render(request, 'landing.html', context)
#  Onboarding guard decorator
def restaurant_verified_required(view_func):
    """
    Ensures the restaurant has completed onboarding AND been approved.
    Otherwise redirect to the appropriate step.
    """
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'restaurant':
            return redirect('customer_dashboard')

        try:
            profile = request.user.restaurant_profile
        except RestaurantProfile.DoesNotExist:
            messages.warning(request, "Please complete your restaurant profile first.")
            return redirect('onboarding_step1')

        if profile.verification_status == 'pending':
            return redirect('onboarding_pending')
        if profile.verification_status == 'rejected':
            return redirect('onboarding_rejected')
        if profile.verification_status == 'suspended':
            return redirect('onboarding_suspended')
        if not profile.is_verified:
            return redirect('onboarding_pending')

        return view_func(request, *args, **kwargs)
    return wrapper


#  ONBOARDING — Step 1: Business Info
@login_required
def onboarding_step1(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    # If already has a profile, pre-fill
    instance = RestaurantProfile.objects.filter(user=request.user).first()

    form = BusinessInfoForm(
        request.POST or None,
        request.FILES or None,
        instance=instance
    )

    if request.method == 'POST' and form.is_valid():
        profile      = form.save(commit=False)
        profile.user = request.user
        profile.save()
        messages.success(request, "Step 1 saved! Now enter your address.")
        return redirect('onboarding_step2')

    return render(request, 'restaurants/onboarding/step1.html', {
        'form': form,
        'step': 1,
        'step_title': 'Business Information',
    })


#  ONBOARDING — Step 2: Address
@login_required
def onboarding_step2(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    profile = get_object_or_404(RestaurantProfile, user=request.user)
    form    = AddressForm(request.POST or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Address saved! Now enter your legal details.")
        return redirect('onboarding_step3')

    return render(request, 'restaurants/onboarding/step2.html', {
        'form': form,
        'step': 2,
        'step_title': 'Restaurant Address',
    })


#  ONBOARDING — Step 3: Legal / Compliance
@login_required
def onboarding_step3(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    profile = get_object_or_404(RestaurantProfile, user=request.user)
    form    = LegalInfoForm(request.POST or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Legal info saved! Now add payment details.")
        return redirect('onboarding_step4')

    return render(request, 'restaurants/onboarding/step3.html', {
        'form': form,
        'step': 3,
        'step_title': 'Legal & Compliance',
    })

#  ONBOARDING — Step 4: Bank Details
@login_required
def onboarding_step4(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    profile  = get_object_or_404(RestaurantProfile, user=request.user)
    instance = BankDetails.objects.filter(restaurant=profile).first()
    form     = BankDetailsForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        bank             = form.save(commit=False)
        bank.restaurant  = profile
        bank.save()
        messages.success(request, "Payment details saved! Finally, upload your documents.")
        return redirect('onboarding_step5')

    return render(request, 'restaurants/onboarding/step4.html', {
        'form': form,
        'step': 4,
        'step_title': 'Payment Details',
    })

#  ONBOARDING — Step 5: Documents
@login_required
def onboarding_step5(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    profile   = get_object_or_404(RestaurantProfile, user=request.user)
    documents = profile.documents.all()
    form      = DocumentUploadForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if 'delete_doc' in request.POST:
            doc_id = request.POST.get('delete_doc')
            RestaurantDocument.objects.filter(
                id=doc_id, restaurant=profile
            ).delete()
            messages.info(request, "Document removed.")
            return redirect('onboarding_step5')

        if form.is_valid():
            doc            = form.save(commit=False)
            doc.restaurant = profile
            doc.save()
            messages.success(request, "Document uploaded successfully.")
            return redirect('onboarding_step5')

    # Check if FSSAI doc has been uploaded (required)
    has_fssai = documents.filter(doc_type='fssai').exists()

    return render(request, 'restaurants/onboarding/step5.html', {
        'form':      form,
        'documents': documents,
        'step':      5,
        'step_title':'Document Upload',
        'has_fssai': has_fssai,
        'profile':   profile,
    })

#  ONBOARDING — Submit for Review
@login_required
def onboarding_submit(request):
    if request.user.role != 'restaurant':
        return redirect('customer_dashboard')

    profile = get_object_or_404(RestaurantProfile, user=request.user)

    # Validate minimum docs
    if not profile.documents.filter(doc_type='fssai').exists():
        messages.error(
            request,
            "Please upload your FSSAI license document before submitting."
        )
        return redirect('onboarding_step5')

    # Already submitted
    if profile.verification_status in ('pending', 'approved'):
        return redirect('onboarding_pending')

    profile.verification_status = 'pending'
    profile.save()

    messages.success(
        request,
        "Your application has been submitted! We'll review it within 2-3 business days."
    )
    return redirect('onboarding_pending')


#  Status Pages
@login_required
def onboarding_pending(request):
    profile = get_object_or_404(RestaurantProfile, user=request.user)
    if profile.is_verified:
        return redirect('restaurant_dashboard')
    return render(request, 'restaurants/onboarding/pending.html', {
        'profile': profile
    })


@login_required
def onboarding_rejected(request):
    profile = get_object_or_404(RestaurantProfile, user=request.user)
    return render(request, 'restaurants/onboarding/rejected.html', {
        'profile': profile
    })


@login_required
def onboarding_suspended(request):
    profile = get_object_or_404(RestaurantProfile, user=request.user)
    return render(request, 'restaurants/onboarding/suspended.html', {
        'profile': profile
    })

#  Helpers
def get_restaurant_profile(request):
    """Shortcut — returns profile or None."""
    try:
        return request.user.restaurant_profile
    except RestaurantProfile.DoesNotExist:
        return None

#  Dashboard Home
@login_required
@restaurant_verified_required
def restaurant_dashboard(request):
    profile = get_restaurant_profile(request)

    # Force fresh querysets — no caching
    menu_items = MenuItem.objects.filter(
        restaurant=profile
    ).select_related('menu_category').order_by('-created_at')

    categories = MenuCategory.objects.filter(
        restaurant=profile
    ).prefetch_related('items')

    # Compute stats directly from DB
    total_items     = menu_items.count()
    available_items = menu_items.filter(is_available=True).count()
    featured_items  = menu_items.filter(is_featured=True).count()

    # Refresh profile from DB to get latest field values
    profile.refresh_from_db()

    context = {
        'profile':         profile,
        'menu_items':      menu_items,
        'categories':      categories,
        'total_items':     total_items,
        'available_items': available_items,
        'featured_items':  featured_items,
        'active_tab':      'dashboard',
    }
    return render(request, 'restaurants/dashboard/home.html', context)

#  Menu Management
@login_required
@restaurant_verified_required
def menu_list(request):
    profile    = get_restaurant_profile(request)
    categories = MenuCategory.objects.filter(
        restaurant=profile
    ).prefetch_related('items')

    # Items without a category
    uncategorized = MenuItem.objects.filter(
        restaurant=profile,
        menu_category=None
    )

    context = {
        'profile':      profile,
        'categories':   categories,
        'uncategorized':uncategorized,
        'active_tab':   'menu',
    }
    return render(request, 'restaurants/dashboard/menu_list.html', context)


@login_required
@restaurant_verified_required
def menu_item_add(request):
    profile = get_restaurant_profile(request)
    form    = MenuItemForm(
        request.POST  or None,
        request.FILES or None,
        restaurant=profile
    )

    if request.method == 'POST' and form.is_valid():
        item            = form.save(commit=False)
        item.restaurant = profile
        item.save()
        messages.success(request, f"'{item.name}' added to your menu!")
        return redirect('menu_list')

    return render(request, 'restaurants/dashboard/menu_item_form.html', {
        'form':       form,
        'profile':    profile,
        'action':     'Add',
        'active_tab': 'menu',
    })


@login_required
@restaurant_verified_required
def menu_item_edit(request, pk):
    profile = get_restaurant_profile(request)
    item    = get_object_or_404(MenuItem, pk=pk, restaurant=profile)
    form    = MenuItemForm(
        request.POST  or None,
        request.FILES or None,
        instance=item,
        restaurant=profile
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"'{item.name}' updated successfully.")
        return redirect('menu_list')

    return render(request, 'restaurants/dashboard/menu_item_form.html', {
        'form':       form,
        'profile':    profile,
        'item':       item,
        'action':     'Edit',
        'active_tab': 'menu',
    })


@login_required
@restaurant_verified_required
def menu_item_delete(request, pk):
    profile = get_restaurant_profile(request)
    item    = get_object_or_404(MenuItem, pk=pk, restaurant=profile)

    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f"'{name}' removed from menu.")
        return redirect('menu_list')

    return render(request, 'restaurants/dashboard/confirm_delete.html', {
        'profile':    profile,
        'item':       item,
        'active_tab': 'menu',
    })


@login_required
@restaurant_verified_required
def menu_item_toggle(request, pk):
    """AJAX-friendly availability toggle."""
    profile = get_restaurant_profile(request)
    item    = get_object_or_404(MenuItem, pk=pk, restaurant=profile)
    item.is_available = not item.is_available
    item.save()
    messages.success(
        request,
        f"'{item.name}' marked as "
        f"{'available' if item.is_available else 'unavailable'}."
    )
    return redirect('menu_list')


#  Menu Categories
@login_required
@restaurant_verified_required
def category_add(request):
    profile = get_restaurant_profile(request)
    form    = MenuCategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cat            = form.save(commit=False)
        cat.restaurant = profile
        cat.save()
        messages.success(request, f"Category '{cat.name}' created.")
        return redirect('menu_list')

    return render(request, 'restaurants/dashboard/category_form.html', {
        'form':       form,
        'profile':    profile,
        'active_tab': 'menu',
    })


@login_required
@restaurant_verified_required
def category_delete(request, pk):
    profile = get_restaurant_profile(request)
    cat     = get_object_or_404(MenuCategory, pk=pk, restaurant=profile)

    if request.method == 'POST':
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect('menu_list')

    return render(request, 'restaurants/dashboard/confirm_delete.html', {
        'profile':    profile,
        'category':   cat,
        'active_tab': 'menu',
    })


#  Restaurant Profile Edit
@login_required
@restaurant_verified_required
def restaurant_profile_edit(request):
    profile = get_restaurant_profile(request)

    # Always refresh from DB before rendering
    profile.refresh_from_db()

    form = RestaurantProfileEditForm(
        request.POST  or None,
        request.FILES or None,
        instance=profile
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            # PRG pattern — redirect prevents re-submit on refresh
            return redirect('restaurant_profile_edit')
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'restaurants/dashboard/profile_edit.html', {
        'form':       form,
        'profile':    profile,
        'active_tab': 'profile',
    })

#  Toggle Restaurant Open/Closed
@login_required
@restaurant_verified_required
def toggle_restaurant_status(request):
    profile          = get_restaurant_profile(request)
    profile.is_open  = not profile.is_open
    profile.save()
    status = "open" if profile.is_open else "closed"
    messages.success(request, f"Your restaurant is now marked as {status}.")
    return redirect('restaurant_dashboard')


#  Restaurant Orders List
@login_required
@restaurant_verified_required
def restaurant_orders(request):
    profile = get_restaurant_profile(request)

    status_filter = request.GET.get('status', '')
    orders = Order.objects.filter(
        restaurant=profile
    ).prefetch_related('items').order_by('-placed_at')

    if status_filter:
        orders = orders.filter(status=status_filter)

    # Counts per status for tabs
    counts = {
        'all':       Order.objects.filter(restaurant=profile).count(),
        'pending':   Order.objects.filter(restaurant=profile, status='pending').count(),
        'confirmed': Order.objects.filter(restaurant=profile, status='confirmed').count(),
        'preparing': Order.objects.filter(restaurant=profile, status='preparing').count(),
        'out':       Order.objects.filter(restaurant=profile, status='out').count(),
        'delivered': Order.objects.filter(restaurant=profile, status='delivered').count(),
        'cancelled': Order.objects.filter(restaurant=profile, status='cancelled').count(),
    }

    return render(request, 'restaurants/dashboard/orders.html', {
        'profile':       profile,
        'orders':        orders,
        'status_filter': status_filter,
        'counts':        counts,
        'active_tab':    'orders',
    })


#  Restaurant Order Detail
@login_required
@restaurant_verified_required
def restaurant_order_detail(request, order_number):
    profile = get_restaurant_profile(request)
    order   = get_object_or_404(
        Order,
        order_number=order_number,
        restaurant=profile
    )
    return render(request, 'restaurants/dashboard/order_detail.html', {
        'profile':    profile,
        'order':      order,
        'active_tab': 'orders',
    })

#  Update Order Status
@login_required
@restaurant_verified_required
@require_POST
def update_order_status(request, order_number):
    profile    = get_restaurant_profile(request)
    order      = get_object_or_404(
        Order,
        order_number=order_number,
        restaurant=profile
    )
    new_status = request.POST.get('status')

    VALID_TRANSITIONS = {
        'pending':   ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['out'],
        'out':       ['delivered'],
        'delivered': [],
        'cancelled': [],
    }

    if new_status in VALID_TRANSITIONS.get(order.status, []):
        order.status = new_status
        if new_status == 'delivered':
            from django.utils import timezone
            order.is_paid = True
            order.paid_at = timezone.now()
        order.save()
        messages.success(
            request,
            f"Order #{order.order_number} marked as "
            f"{order.get_status_display()}."
        )
    else:
        messages.error(
            request,
            f"Cannot change status from "
            f"{order.get_status_display()} to {new_status}."
        )

    return redirect('restaurant_order_detail',
                    order_number=order.order_number)

#  Offer Management
@login_required
@restaurant_verified_required
def offer_list(request):
    profile = get_restaurant_profile(request)
    offers  = Offer.objects.filter(restaurant=profile)
    return render(request, 'restaurants/dashboard/offers.html', {
        'profile':    profile,
        'offers':     offers,
        'active_tab': 'offers',
    })


@login_required
@restaurant_verified_required
def offer_add(request):
    profile = get_restaurant_profile(request)
    form    = OfferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        offer            = form.save(commit=False)
        offer.restaurant = profile
        offer.save()
        messages.success(request, f"Offer '{offer.code}' created!")
        return redirect('offer_list')
    return render(request, 'restaurants/dashboard/offer_form.html', {
        'profile':    profile,
        'form':       form,
        'action':     'Create',
        'active_tab': 'offers',
    })


@login_required
@restaurant_verified_required
def offer_edit(request, pk):
    profile = get_restaurant_profile(request)
    offer   = get_object_or_404(Offer, pk=pk, restaurant=profile)
    form    = OfferForm(request.POST or None, instance=offer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Offer '{offer.code}' updated.")
        return redirect('offer_list')
    return render(request, 'restaurants/dashboard/offer_form.html', {
        'profile':    profile,
        'form':       form,
        'offer':      offer,
        'action':     'Edit',
        'active_tab': 'offers',
    })


@login_required
@restaurant_verified_required
@require_POST
def offer_delete(request, pk):
    profile = get_restaurant_profile(request)
    offer   = get_object_or_404(Offer, pk=pk, restaurant=profile)
    code    = offer.code
    offer.delete()
    messages.success(request, f"Offer '{code}' deleted.")
    return redirect('offer_list')


@login_required
@restaurant_verified_required
@require_POST
def offer_toggle(request, pk):
    profile        = get_restaurant_profile(request)
    offer          = get_object_or_404(Offer, pk=pk, restaurant=profile)
    offer.is_active= not offer.is_active
    offer.save()
    status = "activated" if offer.is_active else "deactivated"
    messages.success(request, f"Offer '{offer.code}' {status}.")
    return redirect('offer_list')

#Analytics view
@login_required
@restaurant_verified_required
def restaurant_analytics(request):
    from orders.models import Order, OrderItem
    profile = get_restaurant_profile(request)

    # Date range
    from django.utils import timezone
    from datetime import timedelta
    now   = timezone.now()
    days  = int(request.GET.get('days', 30))
    start = now - timedelta(days=days)

    orders = Order.objects.filter(
        restaurant=profile,
        placed_at__gte=start
    )

    # Summary stats
    total_orders   = orders.count()
    total_revenue  = orders.filter(
        status='delivered'
    ).aggregate(
        t=Sum('total_amount')
    )['t'] or 0

    avg_order_val  = (
        total_revenue / total_orders
        if total_orders else 0
    )

    delivered      = orders.filter(status='delivered').count()
    cancelled      = orders.filter(status='cancelled').count()
    completion_rate= round(
        (delivered / total_orders * 100) if total_orders else 0, 1
    )

    # Revenue by day
    revenue_by_day = list(
        orders.filter(status='delivered')
        .annotate(day=TruncDate('placed_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'),
                  count=Count('id'))
        .order_by('day')
    )

    # Top selling items
    top_items = list(
        OrderItem.objects.filter(
            order__restaurant=profile,
            order__placed_at__gte=start,
            order__status='delivered'
        )
        .values('item_name')
        .annotate(
            total_qty=Sum('quantity'),
            total_rev=Sum('item_price')
        )
        .order_by('-total_qty')[:5]
    )

    # Orders by status
    status_counts = dict(
        orders.values('status')
        .annotate(c=Count('id'))
        .values_list('status', 'c')
    )

    return render(request, 'restaurants/dashboard/analytics.html', {
        'profile':         profile,
        'active_tab':      'analytics',
        'days':            days,
        'total_orders':    total_orders,
        'total_revenue':   total_revenue,
        'avg_order_val':   round(avg_order_val, 2),
        'delivered':       delivered,
        'cancelled':       cancelled,
        'completion_rate': completion_rate,
        'revenue_by_day':  revenue_by_day,
        'top_items':       top_items,
        'status_counts':   status_counts,
    })
    
#notification view
    
@login_required
@restaurant_verified_required
def restaurant_notifications(request):
    from orders.models import Order
    profile = get_restaurant_profile(request)

    # Recent activity as notifications
    recent_orders = Order.objects.filter(
        restaurant=profile
    ).order_by('-placed_at')[:20]

    notifications = []
    for order in recent_orders:
        icon, color, msg = {
            'pending':   ('bell-fill',       '#f59e0b',
                          f'New order #{order.order_number} received'),
            'confirmed': ('check-circle',    '#60a5fa',
                          f'Order #{order.order_number} confirmed'),
            'preparing': ('fire',            '#a78bfa',
                          f'Preparing order #{order.order_number}'),
            'out':       ('bicycle',         '#ff6b35',
                          f'Order #{order.order_number} out for delivery'),
            'delivered': ('house-check-fill','#10b981',
                          f'Order #{order.order_number} delivered'),
            'cancelled': ('x-circle-fill',  '#f87171',
                          f'Order #{order.order_number} was cancelled'),
        }.get(order.status,
              ('bell', '#6b7280', f'Order #{order.order_number} updated'))

        notifications.append({
            'icon':      icon,
            'color':     color,
            'message':   msg,
            'time':      order.placed_at,
            'order':     order,
        })

    return render(request, 'restaurants/dashboard/notification.html', {
        'profile':       profile,
        'notifications': notifications,
        'active_tab':    'notifications',
    })
    

def search_suggestions(request):
    """
    Returns live search suggestions for restaurants and dishes.
    Used by the landing page hero search.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    from django.db.models import Q
    from .models import MenuItem

    results = []

    # Restaurant suggestions (max 4)
    restaurants = RestaurantProfile.objects.filter(
        is_verified=True
    ).filter(
        Q(restaurant_name__icontains=q) |
        Q(cuisine_type__icontains=q)    |
        Q(city__icontains=q)
    )[:4]

    for r in restaurants:
        results.append({
            'name': r.restaurant_name,
            'sub':  f"{r.get_cuisine_type_display()} · {r.city}",
            'url':  f"/orders/restaurant/{r.pk}/",
            'icon': 'shop',
        })

    # Dish suggestions (max 4)
    dishes = MenuItem.objects.filter(
        is_available=True,
        restaurant__is_verified=True
    ).filter(
        Q(name__icontains=q) |
        Q(description__icontains=q)
    ).select_related('restaurant')[:4]

    for d in dishes:
        results.append({
            'name': d.name,
            'sub':  f"₹{d.price} · {d.restaurant.restaurant_name}",
            'url':  f"/orders/restaurant/{d.restaurant.pk}/",
            'icon': 'egg-fried',
        })

    return JsonResponse({'results': results[:6]})