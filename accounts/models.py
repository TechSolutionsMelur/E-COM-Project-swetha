from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [('customer', 'Customer'), ('restaurant', 'Restaurant')]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True)

    def is_customer(self):
        return self.role == 'customer'

    def is_restaurant(self):
        return self.role == 'restaurant'
    
    def __str__(self):
        return f"{self.username} ({self.role})"

