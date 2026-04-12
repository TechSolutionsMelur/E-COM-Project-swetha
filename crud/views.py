from django.shortcuts import render, redirect
from .models import Food_Product
from .forms import Food_form
from django.http import HttpResponse


# Create your views here.
def test(request):
    queryset = Food_Product.objects.all()
    return render(request, 'crud/home.html', {'queryset': queryset})
def upload(request):
    if request.method == 'POST':
        upload = Food_form(request.POST, request.FILES)
        if upload.is_valid():
            upload.save()
            return redirect('test')
    else:
        upload = Food_form()

    return render(request, 'crud/upload_form.html',{'form':upload})

def update_Food(request,food_id):
    data = None
    #food_id = int(food_id)
    try:
        data = Food_Product.objects.get(id = food_id)     
    except Food_Product.DoesNotExist:
        return redirect('test')
    if request.method == 'POST':
        food_form = Food_form(request.POST , request.FILES, instance = data)
        
        if food_form.is_valid():
            food_form.save()
            return redirect('test')
        else:
            return HttpResponse("""something went wrong. pleade reload the webpage by clicking <a href="{{url:'test'}}>Reload</a>" """)
    return render(request, 'crud/upload_form.html', {'form':Food_form(instance=data)})

def delete_food(request, food_id):
    food_id = int(food_id)
    try:
        data = Food_Product.objects.get(id = food_id)
    except Food_Product.DoesNotExists:
        return redirect('test')
    data.delete()
    return redirect('test')