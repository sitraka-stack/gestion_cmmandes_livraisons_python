from django.contrib import admin
from .models import Fournisseur, Livraison, Produit, Commande, LigneCommande

admin.site.register(Fournisseur)
admin.site.register(Produit)
admin.site.register(Commande)
admin.site.register(LigneCommande)



# ...existing code...

@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('commande', 'statut', 'date_prevue', 'date_effective')
    list_filter = ('statut',)
# ...existing code...