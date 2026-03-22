from django.db import models

# Create your models here.
class Food_Product(models.Model):
    name = models.CharField(max_length=50)
    picture = models.ImageField()
    description = models.TextField(default="available")
    price = models.IntegerField()
    
    def __str__(self):
        return self.name
    