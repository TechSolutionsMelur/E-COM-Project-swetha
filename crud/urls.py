from django.urls import path
from .views import *

urlpatterns = [
    path('', test, name= 'test' ),
    path('upload/', upload, name='upload-food'),
    path('update/<int:food_id>',update_Food),
    path('delete/<int:food_id>', delete_food),

]
