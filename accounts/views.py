from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomerRegisterForm, RestaurantRegisterForm, LoginForm
from .decorators import customer_required, restaurant_required


# ---------- Role Selection ----------
def role_select(request):
    """Landing page for choosing Customer or Restaurant registration."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    return render(request, 'accounts/role.html')


# ---------- Register ----------
def register_customer(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = CustomerRegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your customer account is ready.")
            return redirect('customer_dashboard')
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'accounts/register.html', {
        'form': form,
        'role': 'Customer',
        'role_key': 'customer',
    })


def register_restaurant(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = RestaurantRegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created! Let's set up your restaurant.")
            return redirect('onboarding_step1') 
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'accounts/register.html', {
        'form': form,
        'role': 'Restaurant Owner',
        'role_key': 'restaurant',
    })


# ---------- Login ----------
def user_login(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return _redirect_by_role(user)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'accounts/login.html', {'form': form})


# ---------- Logout ----------
def user_logout(request):
    logout(request)
    messages.info(request, "You've been logged out. See you soon!")
    return redirect('landing')


# ---------- Helper ----------
# In accounts/views.py — update _redirect_by_role:
def _redirect_by_role(user):
    if user.role == 'restaurant':
        try:
            profile = user.restaurant_profile
            # Profile exists — check verification status
            if profile.is_verified:
                return redirect('restaurant_dashboard')
            elif profile.verification_status == 'rejected':
                return redirect('onboarding_rejected')
            else:
                return redirect('onboarding_pending')
        except:
            # No profile yet — send to onboarding
            return redirect('onboarding_step1')
    return redirect('customer_dashboard')