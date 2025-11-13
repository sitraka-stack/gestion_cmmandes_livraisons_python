from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
app_name = 'commandes'

urlpatterns = [
    path('', views.index, name='index'),
    path('produit/<slug:slug>/', views.produit_detail, name='produit-detail'),
    path('produit/<slug:slug>/commander/', views.commander_produit, name='commander-produit'),

    # Fournisseurs (si déjà présents)
    path('fournisseurs/', views.fournisseurs_list, name='fournisseurs-list'),
    path('fournisseurs/add/', views.fournisseur_create, name='fournisseur-add'),
    path('fournisseurs/<int:pk>/edit/', views.fournisseur_edit, name='fournisseur-edit'),
    path('fournisseurs/<int:pk>/delete/', views.fournisseur_delete, name='fournisseur-delete'),

    # Commandes
    path('commandes/', views.commandes_list, name='commandes-list'),
    path('commandes/export/csv/', views.export_commandes_csv, name='commandes-export-csv'),
    path('commandes/json/', views.commandes_json, name='commandes-json'),
    path('commandes/<int:pk>/', views.commande_detail, name='commande-detail'),

    # Livraison (changer statut et infos)
    path('commandes/<int:commande_pk>/livraison/', views.livraison_update, name='livraison-update'),

    path('', views.index, name='index'),  # ou ta vue d'accueil
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='commandes/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='commandes:index'), name='logout'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
]