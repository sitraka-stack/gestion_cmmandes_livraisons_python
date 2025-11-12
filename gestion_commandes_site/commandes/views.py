from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from commandes.models import Produit

# Create your views here.
def index(request):
    produits = Produit.objects.all()

    return render(request, 'commandes/index.html', context={"produits":produits})

def produit_detail(request, slug):
    produit = get_object_or_404(Produit, slug=slug)
    return  render(request, 'commandes/detail.html', context={"produit":produit})