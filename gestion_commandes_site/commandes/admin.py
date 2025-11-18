from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import Fournisseur, Livraison, Produit, Commande, LigneCommande



admin.site.register(Commande)
admin.site.register(LigneCommande)



# ...existing code...

@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('commande', 'statut', 'date_prevue', 'date_effective')
    list_filter = ('statut',)
# ...existing code...

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'user', 'email', 'telephone', 'approved')
    list_filter = ('approved',)
    search_fields = ('nom', 'email', 'user__username')
    actions = ['approve_fournisseurs', 'revoke_approval']

    def approve_fournisseurs(self, request, queryset):
        """Action admin: marque les fournisseurs sélectionnés comme approuvés.
        Envoie un e-mail si la configuration d'e-mail est présente (utile en dev with console backend)."""
        updated = queryset.update(approved=True)
        # envoyer un e-mail de notification si possible
        for f in queryset:
            try:
                if getattr(settings, 'EMAIL_HOST', None) and f.user.email:
                    send_mail(
                        'Votre demande de fournisseur a été approuvée',
                        'Bonjour %s,\n\nVotre compte fournisseur a été approuvé. Vous pouvez désormais ajouter des produits et gérer vos commandes.' % (f.nom or f.user.get_full_name()),
                        getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@localhost'),
                        [f.user.email],
                        fail_silently=True,
                    )
            except Exception:
                # fail silently in admin action
                pass
        self.message_user(request, "%d fournisseur(s) approuvé(s)." % updated)

    approve_fournisseurs.short_description = 'Approuver les fournisseurs sélectionnés'

    def revoke_approval(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, "%d approbation(s) révoquée(s)." % updated)

    revoke_approval.short_description = 'Révoquer l\'approbation des fournisseurs sélectionnés'

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'fournisseur', 'prix', 'is_active')
    list_filter = ('is_active', 'fournisseur')
    search_fields = ('nom', 'slug')
