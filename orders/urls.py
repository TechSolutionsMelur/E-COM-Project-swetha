from django.urls import path
from . import views

urlpatterns = [
    # Customer dashboard
    path('dashboard/',
         views.customer_dashboard,      name='customer_dashboard'),

    # Restaurant detail / menu
    path('restaurant/<int:pk>/',
         views.restaurant_detail,       name='restaurant_detail'),

    # Cart
    path('cart/',
         views.cart_detail,             name='cart_detail'),
    path('cart/add/<int:item_id>/',
         views.add_to_cart,             name='add_to_cart'),
    path('cart/remove/<int:item_id>/',
         views.remove_from_cart,        name='remove_from_cart'),
    path('cart/delete/<int:item_id>/',
         views.delete_from_cart,        name='delete_from_cart'),
    path('cart/clear/',
         views.clear_cart,              name='clear_cart'),

    # Checkout
    path('checkout/',
         views.checkout,                name='checkout'),
    path('checkout/payment/',
         views.checkout_payment,        name='checkout_payment'),

    # Orders
    path('order/success/<str:order_number>/',
         views.order_success,           name='order_success'),
    path('orders/',
         views.order_history,           name='order_history'),
    path('order/<str:order_number>/',
         views.order_detail,            name='order_detail'),
    path('order/<str:order_number>/cancel/',
         views.cancel_order,            name='cancel_order'),
    path('search/',
     views.customer_search, name='customer_search'),
    
    #coupon URLs:
     path('cart/coupon/apply/',
          views.apply_coupon,   name='apply_coupon'),
     path('cart/coupon/remove/',
          views.remove_coupon,  name='remove_coupon'),
]