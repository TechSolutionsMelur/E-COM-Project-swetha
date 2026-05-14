from django.urls import path
from . import views

urlpatterns = [
    path('role-select/',         views.role_select,          name='role_select'),
    path('register/customer/',   views.register_customer,    name='register_customer'),
    path('register/restaurant/', views.register_restaurant,  name='register_restaurant'),
    path('login/',               views.user_login,           name='login'),
    path('logout/',              views.user_logout,          name='logout'),
]