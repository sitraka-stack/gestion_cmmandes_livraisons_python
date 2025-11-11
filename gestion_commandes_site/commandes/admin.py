from django.contrib import admin
from .models import Fournisseur, Produit, Commande, LigneCommande

admin.site.register(Fournisseur)
admin.site.register(Produit)
admin.site.register(Commande)
admin.site.register(LigneCommande)
