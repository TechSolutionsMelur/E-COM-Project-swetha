from django.shortcuts import redirect
from functools import wraps


def customer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'customer':
            return redirect('restaurant_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def restaurant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'restaurant':
            return redirect('customer_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper