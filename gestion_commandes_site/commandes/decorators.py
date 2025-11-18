from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def is_fournisseur(user):
    """Renvoie True si l'utilisateur est authentifié et a un fournisseur_profile lié."""
    return user.is_authenticated and hasattr(user, "fournisseur_profile")

def fournisseur_required(view_func=None, login_url='login'):
    """
    Décorateur pour restreindre l'accès aux vues aux seuls fournisseurs.
    - Si non connecté : redirige vers login_url.
    - Si connecté mais pas fournisseur : lève PermissionDenied (403).
    Utilisation :
      @login_required
      @fournisseur_required
      def ma_vue(request): ...
    """
    def _decorator(func):
        @wraps(func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(login_url)
            if not is_fournisseur(request.user):
                raise PermissionDenied
            return func(request, *args, **kwargs)
        return _wrapped

    if view_func:
        return _decorator(view_func)
    return _decorator