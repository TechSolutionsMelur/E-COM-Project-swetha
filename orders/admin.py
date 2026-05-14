from .models import Order, OrderItem, DeliveryAddress
from django.contrib import admin

class OrderItemInline(admin.TabularInline):
    model         = OrderItem
    extra         = 0
    readonly_fields = ['item_name', 'item_price', 'quantity', 'item_total']
    can_delete    = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = [
        'order_number', 'user', 'restaurant',
        'total_amount', 'status', 'payment_method',
        'is_paid', 'placed_at'
    ]
    list_filter   = ['status', 'payment_method', 'is_paid']
    search_fields = ['order_number', 'user__username',
                     'restaurant__restaurant_name']
    readonly_fields = ['order_number', 'placed_at', 'updated_at']
    list_editable = ['status', 'is_paid']
    inlines       = [OrderItemInline]

@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'label', 'full_name', 'city', 'is_default']
    search_fields = ['user__username', 'full_name', 'city']