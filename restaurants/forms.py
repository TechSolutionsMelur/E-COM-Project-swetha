from django import forms
from .models import Offer
from .models import MenuItem, MenuCategory, RestaurantProfile
from .models import RestaurantProfile, BankDetails, RestaurantDocument


# ─────────────────────────────────────────────
#  Step 1 — Business Info
# ─────────────────────────────────────────────
class BusinessInfoForm(forms.ModelForm):
    class Meta:
        model  = RestaurantProfile
        fields = [
            'restaurant_name', 'owner_name', 'owner_email',
            'owner_phone', 'alternate_phone',
            'cuisine_type', 'description', 'cover_image',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_owner_phone(self):
        phone = self.cleaned_data.get('owner_phone', '')
        digits = phone.replace('+91', '').replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) != 10:
            raise forms.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return phone


# ─────────────────────────────────────────────
#  Step 2 — Address
# ─────────────────────────────────────────────
class AddressForm(forms.ModelForm):
    class Meta:
        model  = RestaurantProfile
        fields = [
            'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'landmark',
        ]

    def clean_pincode(self):
        pin = self.cleaned_data.get('pincode', '')
        if not pin.isdigit() or len(pin) != 6:
            raise forms.ValidationError("Enter a valid 6-digit PIN code.")
        return pin


# ─────────────────────────────────────────────
#  Step 3 — Legal / Compliance
# ─────────────────────────────────────────────
class LegalInfoForm(forms.ModelForm):
    class Meta:
        model  = RestaurantProfile
        fields = [
            'fssai_license_number', 'business_license_number',
            'gst_number', 'pan_number',
            'opening_time', 'closing_time',
            'avg_delivery_time', 'min_order_amount',
        ]
        widgets = {
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_fssai_license_number(self):
        fssai = self.cleaned_data.get('fssai_license_number', '').strip()
        if not fssai.isdigit() or len(fssai) != 14:
            raise forms.ValidationError(
                "FSSAI license must be exactly 14 digits."
            )
        return fssai

    def clean_gst_number(self):
        gst = self.cleaned_data.get('gst_number', '').strip().upper()
        if gst and len(gst) != 15:
            raise forms.ValidationError("GST number must be exactly 15 characters.")
        return gst

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').strip().upper()
        if pan and len(pan) != 10:
            raise forms.ValidationError("PAN number must be exactly 10 characters.")
        return pan

    def clean(self):
        cleaned = super().clean()
        opening = cleaned.get('opening_time')
        closing = cleaned.get('closing_time')
        if opening and closing and closing <= opening:
            raise forms.ValidationError(
                "Closing time must be after opening time."
            )
        return cleaned


# ─────────────────────────────────────────────
#  Step 4 — Bank / Payment Details
# ─────────────────────────────────────────────
class BankDetailsForm(forms.ModelForm):
    confirm_account = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.PasswordInput(),
        label="Confirm Account Number",
    )

    class Meta:
        model  = BankDetails
        fields = [
            'payment_mode',
            'account_holder_name', 'account_number',
            'ifsc_code', 'bank_name', 'branch_name',
            'upi_id',
        ]
        widgets = {
            'account_number': forms.PasswordInput(render_value=True),
        }

    def clean(self):
        cleaned = super().clean()
        mode    = cleaned.get('payment_mode')

        if mode in ('bank', 'both'):
            required_bank = [
                'account_holder_name', 'account_number',
                'ifsc_code', 'bank_name',
            ]
            for field in required_bank:
                if not cleaned.get(field):
                    self.add_error(field, "This field is required for bank payments.")

            acc     = cleaned.get('account_number', '')
            confirm = cleaned.get('confirm_account', '')
            if acc and confirm and acc != confirm:
                self.add_error('confirm_account', "Account numbers do not match.")

            ifsc = cleaned.get('ifsc_code', '').upper()
            if ifsc and len(ifsc) != 11:
                self.add_error('ifsc_code', "IFSC code must be 11 characters.")

        if mode in ('upi', 'both'):
            if not cleaned.get('upi_id'):
                self.add_error('upi_id', "UPI ID is required.")
            else:
                upi = cleaned.get('upi_id', '')
                if '@' not in upi:
                    self.add_error('upi_id', "Enter a valid UPI ID (e.g. name@upi).")

        return cleaned


# ─────────────────────────────────────────────
#  Step 5 — Document Upload
# ─────────────────────────────────────────────
class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model  = RestaurantDocument
        fields = ['doc_type', 'file', 'description']

    ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'webp']
    MAX_SIZE_MB = 5

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            ext = f.name.lower().split('.')[-1]
            if ext not in self.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f"Only {', '.join(self.ALLOWED_EXTENSIONS)} files are allowed."
                )
            if f.size > self.MAX_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f"File size must not exceed {self.MAX_SIZE_MB} MB."
                )
        return f


# ─────────────────────────────────────────────
#  Menu Item Form
# ─────────────────────────────────────────────
class MenuItemForm(forms.ModelForm):
    class Meta:
        model  = MenuItem
        fields = [
            'name', 'description', 'price',
            'menu_category', 'item_type',
            'image', 'is_available', 'is_featured',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, restaurant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if restaurant:
            self.fields['menu_category'].queryset = MenuCategory.objects.filter(
                restaurant=restaurant
            )

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price


# ─────────────────────────────────────────────
#  Menu Category Form
# ─────────────────────────────────────────────
class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model  = MenuCategory
        fields = ['name', 'sort_order']


# ─────────────────────────────────────────────
#  Restaurant Profile Edit Form
# ─────────────────────────────────────────────
class RestaurantProfileEditForm(forms.ModelForm):
    class Meta:
        model  = RestaurantProfile
        fields = [
            'restaurant_name', 'description',
            'cuisine_type', 'cover_image',
            'owner_phone', 'alternate_phone',
            'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'landmark',
            'opening_time', 'closing_time',
            'avg_delivery_time', 'min_order_amount',
            'is_open', 'accepts_online_orders',
        ]
        widgets = {
            'description':  forms.Textarea(attrs={'rows': 3}),
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class OfferForm(forms.ModelForm):
    class Meta:
        model  = Offer
        fields = [
            'title', 'description', 'code',
            'discount_type', 'discount_value',
            'min_order_value', 'max_discount',
            'usage_limit', 'is_active',
            'valid_from', 'valid_until',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'valid_from':  forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'valid_until': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code.isalnum():
            raise forms.ValidationError(
                "Code must contain only letters and numbers."
            )
        return code

    def clean(self):
        cleaned = super().clean()
        valid_from  = cleaned.get('valid_from')
        valid_until = cleaned.get('valid_until')
        if valid_from and valid_until and valid_until <= valid_from:
            raise forms.ValidationError(
                "Valid until must be after valid from."
            )
        return cleaned