from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'commandes'

urlpatterns = [
    # index / produits / panier / auth
    path('', views.index, name='index'),
    path('produit/<slug:slug>/', views.produit_detail, name='produit-detail'),
    path('produit/<slug:slug>/commander/', views.commander_produit, name='commander-produit'),

    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),

    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='commandes/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='commandes:index'), name='logout'),

    # Commandes (client / admin)
    path('commandes/list/', views.commandes_list, name='commandes-list'),
    path('commandes/mes/', views.mes_commandes, name='mes-commandes'),
    path('commandes/export/csv/', views.export_commandes_csv, name='commandes-export-csv'),
    path('commandes/json/', views.commandes_json, name='commandes-json'),
    path('commandes/<int:pk>/', views.commande_detail, name='commande-detail'),
    path('commandes/<int:commande_pk>/livraison/', views.livraison_update, name='livraison-update'),

    # Fournisseurs (regroupés sous /fournisseur/ pour éviter collisions)
    path('fournisseur/devenir/', views.DevenirFournisseurView.as_view(), name='devenir'),
    path('fournisseur/attente/', views.AttenteApprobationView.as_view(), name='attente_approbation'),
    path('fournisseur/dashboard/', views.FournisseurDashboardView.as_view(), name='dashboard'),
    path('fournisseur/produit/add/', views.ProduitCreateView.as_view(), name='produit_add'),
    path('fournisseur/produit/<int:pk>/edit/', views.ProduitUpdateView.as_view(), name='produit_edit'),
    path('fournisseur/produit/<int:pk>/delete/', views.ProduitDeleteView.as_view(), name='produit_delete'),
    path('fournisseur/ventes/', views.VentesFournisseurView.as_view(), name='ventes'),
    path('fournisseur/commandes/', views.CommandesFournisseurListView.as_view(), name='commandes-fournisseur'),
    path('fournisseur/livraisons/', views.LivraisonFournisseurListView.as_view(), name='livraisons-fournisseur'),
    path('fournisseur/commande/<int:pk>/marquer-prete/', views.MarquerPreteView.as_view(), name='marquer_prete'),
    path("livraisons/", views.dashboard_livraison, name="dashboard_livraison"),
    path("livraison/<int:pk>/<str:statut>/", views.modifier_statut_livraison, name="modifier_statut_livraison"),
    
]