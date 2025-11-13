from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # routes de l'app "commandes" (index, produits, fournisseurs, commandes, livraison, etc.)
    path('', include(('commandes.urls', 'commandes'), namespace='commandes')),

    # admin Django
    path('admin/', admin.site.urls),
]

# servir les médias en dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)