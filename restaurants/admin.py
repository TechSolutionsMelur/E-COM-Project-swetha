from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import Category, MenuItem
from .models import Offer
from .models import RestaurantProfile, BankDetails, RestaurantDocument




# ─────────────────────────────────────────────
#  Inline: Documents
# ─────────────────────────────────────────────
class DocumentInline(admin.TabularInline):
    model  = RestaurantDocument
    extra  = 0
    fields = ['doc_type', 'file', 'description', 'uploaded_at']
    readonly_fields = ['uploaded_at']


# ─────────────────────────────────────────────
#  Inline: Bank Details
# ─────────────────────────────────────────────
class BankDetailsInline(admin.StackedInline):
    model       = BankDetails
    extra       = 0
    fields      = [
        'payment_mode',
        'account_holder_name', 'account_number',
        'ifsc_code', 'bank_name', 'branch_name',
        'upi_id',
    ]
    # Mask account number in admin
    readonly_fields = ['masked_account']

    def masked_account(self, obj):
        if obj.account_number:
            masked = '*' * (len(obj.account_number) - 4) + obj.account_number[-4:]
            return masked
        return '—'
    masked_account.short_description = 'Account (masked)'


# ─────────────────────────────────────────────
#  Main: Restaurant Profile Admin
# ─────────────────────────────────────────────
@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    inlines = [BankDetailsInline, DocumentInline]

    list_display = [
        'restaurant_name', 'owner_name', 'owner_phone',
        'city', 'fssai_license_number',
        'status_badge', 'submitted_at', 'approval_actions',
    ]
    list_filter  = ['verification_status', 'cuisine_type', 'city', 'state']
    search_fields= [
        'restaurant_name', 'owner_name', 'owner_email',
        'fssai_license_number', 'city',
    ]
    ordering     = ['-submitted_at']
    actions      = ['approve_selected', 'reject_selected', 'suspend_selected']

    readonly_fields = [
        'submitted_at', 'updated_at',
        'verified_at', 'verified_by',
        'full_address_display', 'status_badge',
    ]

    fieldsets = (
        ('🏪 Basic Information', {
            'fields': (
                'user', 'restaurant_name', 'owner_name',
                'owner_email', 'owner_phone', 'alternate_phone',
                'cuisine_type', 'description', 'cover_image',
            )
        }),
        ('📍 Address', {
            'fields': (
                'address_line1', 'address_line2',
                'city', 'state', 'pincode', 'landmark',
                'full_address_display',
            )
        }),
        ('📋 Legal & Compliance', {
            'fields': (
                'fssai_license_number', 'business_license_number',
                'gst_number', 'pan_number',
            )
        }),
        ('⏰ Operations', {
            'fields': (
                'opening_time', 'closing_time',
                'avg_delivery_time', 'min_order_amount',
            )
        }),
        ('✅ Verification', {
            'fields': (
                'is_verified', 'verification_status',
                'rejection_reason',
                'verified_at', 'verified_by',
            ),
            'classes': ('wide',),
        }),
        ('🕒 Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Custom columns ──
    def status_badge(self, obj):
        colors = {
            'pending':   ('#f59e0b', '⏳'),
            'approved':  ('#10b981', '✅'),
            'rejected':  ('#ef4444', '❌'),
            'suspended': ('#6b7280', '🚫'),
        }
        color, icon = colors.get(obj.verification_status, ('#6b7280', '?'))
        return format_html(
            '<span style="color:{}; font-weight:600;">{} {}</span>',
            color, icon, obj.get_verification_status_display()
        )
    status_badge.short_description = 'Status'

    def approval_actions(self, obj):
        if obj.verification_status == 'pending':
            return format_html(
                '<a href="{}?action=approve" style="color:green; margin-right:8px;">✅ Approve</a>'
                '<a href="{}?action=reject"  style="color:red;">❌ Reject</a>',
                f'/admin/restaurants/restaurantprofile/{obj.pk}/change/',
                f'/admin/restaurants/restaurantprofile/{obj.pk}/change/',
            )
        return format_html('<span style="color:#6b7280;">—</span>')
    approval_actions.short_description = 'Quick Actions'

    def full_address_display(self, obj):
        return obj.full_address
    full_address_display.short_description = 'Full Address'

    # ── Bulk actions ──
    @admin.action(description='✅ Approve selected restaurants')
    def approve_selected(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.approve(request.user)
            count += 1
        self.message_user(
            request,
            f"{count} restaurant(s) approved successfully.",
            messages.SUCCESS
        )

    @admin.action(description='❌ Reject selected restaurants')
    def reject_selected(self, request, queryset):
        for profile in queryset:
            profile.reject(reason='Rejected via bulk action — contact support.')
        self.message_user(
            request,
            f"{queryset.count()} restaurant(s) rejected.",
            messages.WARNING
        )

    @admin.action(description='🚫 Suspend selected restaurants')
    def suspend_selected(self, request, queryset):
        for profile in queryset:
            profile.suspend()
        self.message_user(
            request,
            f"{queryset.count()} restaurant(s) suspended.",
            messages.WARNING
        )

    # ── Handle approve/reject via URL param ──
    def change_view(self, request, object_id, form_url='', extra_context=None):
        action = request.GET.get('action')
        if action in ('approve', 'reject'):
            obj = self.get_object(request, object_id)
            if action == 'approve':
                obj.approve(request.user)
                self.message_user(request, f"✅ {obj.restaurant_name} approved!", messages.SUCCESS)
            elif action == 'reject':
                obj.reject(reason='Rejected by admin — please resubmit with correct documents.')
                self.message_user(request, f"❌ {obj.restaurant_name} rejected.", messages.WARNING)
            return self.response_post_save_change(request, obj)
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(RestaurantDocument)
class RestaurantDocumentAdmin(admin.ModelAdmin):
    list_display  = ['restaurant', 'doc_type', 'filename', 'uploaded_at']
    list_filter   = ['doc_type']
    search_fields = ['restaurant__restaurant_name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'icon', 'slug', 'sort_order']
    prepopulated_fields = {'slug': ('name',)}
    ordering      = ['sort_order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display  = ['name', 'restaurant', 'menu_category', 'price',
                     'item_type', 'is_available', 'is_featured']
    list_filter   = ['item_type', 'is_available', 'is_featured', 'menu_category']
    search_fields = ['name', 'restaurant__restaurant_name']
    list_editable = ['is_available', 'is_featured', 'price']


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display  = [
        'code', 'restaurant', 'discount_type',
        'discount_value', 'used_count',
        'is_active', 'valid_until'
    ]
    list_filter   = ['discount_type', 'is_active']
    search_fields = ['code', 'restaurant__restaurant_name']
    list_editable = ['is_active']