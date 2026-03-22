from django import forms
from .models import Food_Product

class Food_form(forms.ModelForm):
    class Meta:
        model = Food_Product
        fields = '__all__'
         
    