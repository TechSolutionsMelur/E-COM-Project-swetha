from django import forms
from .models import DeliveryAddress, Order


class DeliveryAddressForm(forms.ModelForm):
    class Meta:
        model  = DeliveryAddress
        fields = [
            'label', 'full_name', 'phone',
            'address_line1', 'address_line2',
            'city', 'state', 'pincode',
            'landmark', 'is_default',
        ]

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        digits = phone.replace('+91', '').replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) != 10:
            raise forms.ValidationError(
                "Enter a valid 10-digit mobile number."
            )
        return phone

    def clean_pincode(self):
        pin = self.cleaned_data.get('pincode', '')
        if not pin.isdigit() or len(pin) != 6:
            raise forms.ValidationError(
                "Enter a valid 6-digit PIN code."
            )
        return pin


class CheckoutForm(forms.Form):
    address_id      = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    payment_method  = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD,
        initial='cod'
    )
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        max_length=300
    )