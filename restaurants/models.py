from django.db import models
from django.conf import settings
from django.utils import timezone



# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def restaurant_doc_path(instance, filename):
    """Uploads to: media/restaurant_docs/<user_id>/<filename>"""
    return f"restaurant_docs/{instance.restaurant.user.id}/{filename}"


def restaurant_image_path(instance, filename):
    return f"restaurant_images/{instance.user.id}/{filename}"


# ─────────────────────────────────────────────
#  Restaurant Profile
# ─────────────────────────────────────────────
class RestaurantProfile(models.Model):

    CUISINE_CHOICES = [
        ('indian',      'Indian'),
        ('chinese',     'Chinese'),
        ('continental', 'Continental'),
        ('italian',     'Italian'),
        ('mexican',     'Mexican'),
        ('fast_food',   'Fast Food'),
        ('south_indian','South Indian'),
        ('north_indian','North Indian'),
        ('bakery',      'Bakery & Desserts'),
        ('beverages',   'Beverages'),
        ('other',       'Other'),
    ]

    VERIFICATION_STATUS = [
        ('pending',   'Pending Review'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('suspended', 'Suspended'),
    ]

    # ── Link to auth user ──
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='restaurant_profile'
    )

    # ── Basic Info ──
    restaurant_name  = models.CharField(max_length=150)
    owner_name       = models.CharField(max_length=100)
    owner_email      = models.EmailField()
    owner_phone      = models.CharField(max_length=15)
    alternate_phone  = models.CharField(max_length=15, blank=True)
    cuisine_type     = models.CharField(max_length=30, choices=CUISINE_CHOICES, default='other')
    description      = models.TextField(blank=True)
    cover_image      = models.ImageField(
        upload_to=restaurant_image_path,
        blank=True, null=True
    )

    # ── Address ──
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100)
    state         = models.CharField(max_length=100)
    pincode       = models.CharField(max_length=10)
    landmark      = models.CharField(max_length=150, blank=True)

    # ── Legal / Compliance ──
    fssai_license_number   = models.CharField(max_length=20, unique=True)
    business_license_number= models.CharField(max_length=50, blank=True)
    gst_number             = models.CharField(max_length=20, blank=True)
    pan_number             = models.CharField(max_length=15, blank=True)

    # ── Operational ──
    opening_time   = models.TimeField(default='09:00')
    closing_time   = models.TimeField(default='22:00')
    avg_delivery_time = models.PositiveIntegerField(
        default=30, help_text="Average delivery time in minutes"
    )
    min_order_amount  = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00
    )
    is_open = models.BooleanField(default=True)
    accepts_online_orders = models.BooleanField(default=True)
    total_orders = models.PositiveIntegerField(default=0)

    # ── Verification ──
    is_verified         = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    rejection_reason    = models.TextField(blank=True)
    verified_at         = models.DateTimeField(null=True, blank=True)
    verified_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_restaurants'
    )

    # ── Timestamps ──
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Restaurant Profile'
        verbose_name_plural = 'Restaurant Profiles'
        ordering            = ['-submitted_at']

    def __str__(self):
        return f"{self.restaurant_name} [{self.verification_status}]"

    def approve(self, admin_user):
        self.is_verified         = True
        self.verification_status = 'approved'
        self.verified_at         = timezone.now()
        self.verified_by         = admin_user
        self.rejection_reason    = ''
        self.save()

    def reject(self, reason=''):
        self.is_verified         = False
        self.verification_status = 'rejected'
        self.rejection_reason    = reason
        self.save()

    def suspend(self):
        self.is_verified         = False
        self.verification_status = 'suspended'
        self.save()

    @property
    def full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts += [self.city, self.state, self.pincode]
        return ', '.join(parts)


# ─────────────────────────────────────────────
#  Bank / Payment Details  (kept separate for security)
# ─────────────────────────────────────────────
class BankDetails(models.Model):
    PAYMENT_MODE = [
        ('bank',   'Bank Account'),
        ('upi',    'UPI ID'),
        ('both',   'Both'),
    ]

    restaurant   = models.OneToOneField(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='bank_details'
    )
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE, default='bank')

    # Bank fields
    account_holder_name = models.CharField(max_length=100, blank=True)
    account_number      = models.CharField(max_length=20,  blank=True)
    confirm_account     = models.CharField(
        max_length=20, blank=True,
        help_text="Not stored — used only for validation"
    )
    ifsc_code           = models.CharField(max_length=15,  blank=True)
    bank_name           = models.CharField(max_length=100, blank=True)
    branch_name         = models.CharField(max_length=100, blank=True)

    # UPI field
    upi_id = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Bank Details'
        verbose_name_plural = 'Bank Details'

    def __str__(self):
        return f"Payment — {self.restaurant.restaurant_name}"

    def save(self, *args, **kwargs):
        # Never persist the confirm_account field
        self.confirm_account = ''
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────
#  Documents
# ─────────────────────────────────────────────
class RestaurantDocument(models.Model):
    DOC_TYPE = [
        ('fssai',      'FSSAI License'),
        ('business',   'Business License'),
        ('gst',        'GST Certificate'),
        ('pan',        'PAN Card'),
        ('bank',       'Bank Proof / Cancelled Cheque'),
        ('identity',   'Owner Identity Proof'),
        ('restaurant', 'Restaurant Photo'),
        ('other',      'Other'),
    ]

    restaurant  = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type    = models.CharField(max_length=20, choices=DOC_TYPE)
    file        = models.FileField(upload_to=restaurant_doc_path)
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Restaurant Document'
        verbose_name_plural = 'Restaurant Documents'

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.restaurant.restaurant_name}"

    def filename(self):
        return self.file.name.split('/')[-1]

    def is_image(self):
        ext = self.file.name.lower().split('.')[-1]
        return ext in ['jpg', 'jpeg', 'png', 'webp']
# ─────────────────────────────────────────────
#  Category (for landing page filter pills)
# ─────────────────────────────────────────────
class Category(models.Model):
    name       = models.CharField(max_length=100)
    icon       = models.CharField(
        max_length=50, default='bi-grid',
        help_text="Bootstrap icon class e.g. bi-egg-fried"
    )
    slug       = models.SlugField(unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering            = ['sort_order']

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  Menu Item
# ─────────────────────────────────────────────
class MenuItem(models.Model):
    ITEM_TYPE = [
        ('veg',     'Vegetarian'),
        ('nonveg',  'Non-Vegetarian'),
        ('vegan',   'Vegan'),
    ]

    restaurant   = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='menu_items'
    )
    menu_category = models.ForeignKey(
    'MenuCategory',
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='items'
    )
    name         = models.CharField(max_length=150)
    description  = models.TextField(blank=True)
    price        = models.DecimalField(max_digits=8, decimal_places=2)
    image        = models.ImageField(
        upload_to='menu_items/', blank=True, null=True
    )
    item_type    = models.CharField(
        max_length=10, choices=ITEM_TYPE, default='veg'
    )
    is_available = models.BooleanField(default=True)
    is_featured  = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.restaurant.restaurant_name}"
    
    
# ─────────────────────────────────────────────
#  Menu Category (restaurant-specific)
# ─────────────────────────────────────────────
class MenuCategory(models.Model):
    restaurant = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='menu_categories'
    )
    name       = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Menu Categories'
        ordering            = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} — {self.restaurant.restaurant_name}"



# ─────────────────────────────────────────────
#  Offer / Discount
# ─────────────────────────────────────────────
class Offer(models.Model):

    DISCOUNT_TYPE = [
        ('percent',  'Percentage Off'),
        ('flat',     'Flat Amount Off'),
        ('delivery', 'Free Delivery'),
        ('bogo',     'Buy 1 Get 1'),
    ]

    restaurant      = models.ForeignKey(
        RestaurantProfile,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    title           = models.CharField(max_length=100)
    description     = models.TextField(blank=True)
    code            = models.CharField(
        max_length=20,
        unique=True,
        help_text="Promo code e.g. SAVE20"
    )
    discount_type   = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE,
        default='percent'
    )
    discount_value  = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Percentage or flat amount"
    )
    min_order_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Minimum cart value to apply offer"
    )
    max_discount    = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Max discount cap for percent type"
    )
    usage_limit     = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited"
    )
    used_count      = models.PositiveIntegerField(default=0)
    is_active       = models.BooleanField(default=True)
    valid_from      = models.DateTimeField(default=timezone.now)
    valid_until     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering    = ['-created_at']
        verbose_name= 'Offer'

    def __str__(self):
        return f"{self.code} — {self.restaurant.restaurant_name}"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, cart_total):
        """Returns discount amount for a given cart total."""
        if not self.is_valid:
            return 0
        if cart_total < self.min_order_value:
            return 0

        if self.discount_type == 'percent':
            discount = (cart_total * self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return round(discount, 2)

        elif self.discount_type == 'flat':
            return min(self.discount_value, cart_total)

        elif self.discount_type == 'delivery':
            return 40  # Covers full delivery fee

        elif self.discount_type == 'bogo':
            return 0   # Handled at item level in future

        return 0