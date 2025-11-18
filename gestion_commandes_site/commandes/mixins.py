from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect

class FournisseurRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = getattr(self.request, 'user', None)
        return user and user.is_authenticated and hasattr(user, 'fournisseur_profile') and user.fournisseur_profile.approved

    def handle_no_permission(self):
        # redirige vers page d'inscription fournisseur si non profil, ou page attente si non approuvé
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return redirect('commandes:login')
        if not hasattr(user, 'fournisseur_profile'):
            return redirect('commandes:devenir')
        return redirect('commandes:attente_approbation')