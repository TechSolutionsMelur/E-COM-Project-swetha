from django.urls import path
from . import views

urlpatterns = [
    # Landing
    path('', views.landing_page, name='landing'),

    # ── Onboarding ──
    path('onboarding/step/1/', views.onboarding_step1,   name='onboarding_step1'),
    path('onboarding/step/2/', views.onboarding_step2,   name='onboarding_step2'),
    path('onboarding/step/3/', views.onboarding_step3,   name='onboarding_step3'),
    path('onboarding/step/4/', views.onboarding_step4,   name='onboarding_step4'),
    path('onboarding/step/5/', views.onboarding_step5,   name='onboarding_step5'),
    path('onboarding/submit/', views.onboarding_submit,  name='onboarding_submit'),

    # ── Onboarding Status ──
    path('onboarding/pending/',   views.onboarding_pending,   name='onboarding_pending'),
    path('onboarding/rejected/',  views.onboarding_rejected,  name='onboarding_rejected'),
    path('onboarding/suspended/', views.onboarding_suspended, name='onboarding_suspended'),

    # ── Dashboard ──
    path('dashboard/',
         views.restaurant_dashboard,    name='restaurant_dashboard'),
    path('dashboard/menu/',
         views.menu_list,               name='menu_list'),
    path('dashboard/menu/add/',
         views.menu_item_add,           name='menu_item_add'),
    path('dashboard/menu/<int:pk>/edit/',
         views.menu_item_edit,          name='menu_item_edit'),
    path('dashboard/menu/<int:pk>/delete/',
         views.menu_item_delete,        name='menu_item_delete'),
    path('dashboard/menu/<int:pk>/toggle/',
         views.menu_item_toggle,        name='menu_item_toggle'),

    # ── Menu Categories ──
    path('dashboard/category/add/',
         views.category_add,            name='category_add'),
    path('dashboard/category/<int:pk>/delete/',
         views.category_delete,         name='category_delete'),

    # ── Profile ──
    path('dashboard/profile/',
         views.restaurant_profile_edit, name='restaurant_profile_edit'),
    path('dashboard/toggle-status/',
         views.toggle_restaurant_status,name='toggle_restaurant_status'),
    
    
     path('dashboard/orders/',
          views.restaurant_orders,        name='restaurant_orders'),
     path('dashboard/orders/<str:order_number>/',
          views.restaurant_order_detail,  name='restaurant_order_detail'),
     path('dashboard/orders/<str:order_number>/update/',
          views.update_order_status,      name='update_order_status'),
     
     # Add offer URLs:
     path('dashboard/offers/',
          views.offer_list,    name='offer_list'),
     path('dashboard/offers/add/',
          views.offer_add,     name='offer_add'),
     path('dashboard/offers/<int:pk>/edit/',
          views.offer_edit,    name='offer_edit'),
     path('dashboard/offers/<int:pk>/delete/',
          views.offer_delete,  name='offer_delete'),
     path('dashboard/offers/<int:pk>/toggle/',
          views.offer_toggle,  name='offer_toggle'),
     
     #notification
     path('dashboard/notifications/', 
          views.restaurant_notifications, name='restaurant_notifications'),
     
     # Analytics
     path('dashboard/analytics/',
     views.restaurant_analytics, name='restaurant_analytics'),
     
     #search suggestions
     path('search-suggestions/',
     views.search_suggestions, name='search_suggestions'),
]