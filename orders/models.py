from django.db import models
from django.conf import settings
from restaurants.models import RestaurantProfile, MenuItem

#  Cart
class Cart(models.Model):
    user       = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='carts'
    )
    applied_offer    = models.ForeignKey(
        'restaurants.Offer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='carts'
    )
    discount_amount  = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )

    def clear(self):
        self.items.all().delete()
        self.restaurant      = None
        self.applied_offer   = None
        self.discount_amount = 0
        self.save()

    # Update Cart.subtotal property to account for discount:
    @property
    def discounted_total(self):
        return max(self.subtotal - self.discount_amount, 0)

    class Meta:
        verbose_name = 'Cart'

    def __str__(self):
        return f"Cart — {self.user.username}"

    # ── Computed properties ──
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.item_total for item in self.items.all())

    @property
    def is_empty(self):
        return not self.items.exists()

    def clear(self):
        self.items.all().delete()
        self.restaurant = None
        self.save()


#  Cart Item
class CartItem(models.Model):
    cart      = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity  = models.PositiveIntegerField(default=1)
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'menu_item')
        ordering        = ['added_at']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    @property
    def item_total(self):
        return self.menu_item.price * self.quantity
    
import uuid

#  Delivery Address (saved per order)
class DeliveryAddress(models.Model):
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    label        = models.CharField(
        max_length=30,
        default='Home',
        help_text="e.g. Home, Work, Other"
    )
    full_name    = models.CharField(max_length=100)
    phone        = models.CharField(max_length=15)
    address_line1= models.CharField(max_length=255)
    address_line2= models.CharField(max_length=255, blank=True)
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=100)
    pincode      = models.CharField(max_length=10)
    landmark     = models.CharField(max_length=150, blank=True)
    is_default   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering    = ['-is_default', '-created_at']
        verbose_name= 'Delivery Address'

    def __str__(self):
        return f"{self.label} — {self.full_name}, {self.city}"

    @property
    def full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts += [self.city, self.state, self.pincode]
        return ', '.join(parts)

    def save(self, *args, **kwargs):
        # Only one default address per user
        if self.is_default:
            DeliveryAddress.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


#  Order
class Order(models.Model):

    PAYMENT_METHOD = [
        ('cod',    'Cash on Delivery'),
        ('upi',    'UPI'),
        ('card',   'Credit / Debit Card'),
        ('wallet', 'Wallet'),
    ]

    ORDER_STATUS = [
        ('pending',    'Pending'),
        ('confirmed',  'Confirmed'),
        ('preparing',  'Preparing'),
        ('out',        'Out for Delivery'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
    ]

    # IDs
    order_number    = models.CharField(
        max_length=12,
        unique=True,
        editable=False
    )

    # Relations
    user            = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    restaurant      = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )

    # Address snapshot (store at time of order)
    delivery_name   = models.CharField(max_length=100)
    delivery_phone  = models.CharField(max_length=15)
    delivery_address= models.TextField()
    delivery_city   = models.CharField(max_length=100)
    delivery_pincode= models.CharField(max_length=10)

    # Financials
    subtotal        = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    delivery_fee    = models.DecimalField(
        max_digits=6, decimal_places=2, default=40
    )
    taxes           = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    applied_offer_code = models.CharField(max_length=20, blank=True)
    discount_amount    = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount    = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    # Payment
    payment_method  = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD,
        default='cod'
    )
    is_paid         = models.BooleanField(default=False)
    paid_at         = models.DateTimeField(null=True, blank=True)

    # Status
    status          = models.CharField(
        max_length=15,
        choices=ORDER_STATUS,
        default='pending'
    )

    # Notes
    special_instructions = models.TextField(blank=True)

    # Timestamps
    placed_at       = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering    = ['-placed_at']
        verbose_name= 'Order'

    def __str__(self):
        return f"Order #{self.order_number} — {self.user}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_number():
        """FD + 8 uppercase hex chars e.g. FD3A9F2C1B"""
        return 'FD' + uuid.uuid4().hex[:8].upper()

    @property
    def status_color(self):
        colors = {
            'pending':   'warning',
            'confirmed': 'info',
            'preparing': 'info',
            'out':       'primary',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')

    @property
    def can_cancel(self):
        return self.status in ('pending', 'confirmed')


#  Order Item (snapshot of menu item at order time)

class OrderItem(models.Model):
    order      = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item  = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True
    )
    # Snapshot fields — frozen at order time
    item_name  = models.CharField(max_length=150)
    item_price = models.DecimalField(max_digits=8, decimal_places=2)
    item_type  = models.CharField(max_length=10, default='veg')
    quantity   = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Order Item'

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"

    @property
    def item_total(self):
        return self.item_price * self.quantity