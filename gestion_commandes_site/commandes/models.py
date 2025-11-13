from django.db import models
from PIL import Image

# Create your models here.
class Fournisseur(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=15)
    adresse = models.TextField()

    def __str__(self):
        return self.nom

class Produit(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(max_length=128)
    images = models.ImageField(upload_to="produits", blank=True, null=True)
    description = models.TextField()
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
    quantite_minimale = models.PositiveIntegerField(default=1, help_text="Quantité minimale de commande")

    def __str__(self):
        return f"{self.nom} (Min: {self.quantite_minimale})"

class Commande(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('en_attente', 'En attente'),
            ('en_cours', 'En cours de livraison'),
            ('livree', 'Livrée'),
            ('annulee', 'Annulée'),
        ],
        default='en_attente'
    )

    def __str__(self):
        return f"Commande {self.id} - {self.produit.nom}"

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()

    def __str__(self):
        return f"Ligne de commande {self.id} - {self.produit.nom}"

class Livraison(models.Model):
    TRANSPORT_CHOICES = [
        ('moto', 'Moto'),
        ('voiture', 'Voiture'),
        ('a_pied', 'À pied'),
        ('trottinette', 'Trottinette'),
    ]

    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='livraison')
    transport = models.CharField(max_length=30, choices=TRANSPORT_CHOICES, blank=True, null=True)
    adresse_livraison = models.CharField(max_length=255, blank=True)
    montant = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    date_prevue = models.DateTimeField(null=True, blank=True)
    date_effective = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('prep', 'Préparée'),
            ('en_transit', 'En transit'),
            ('livree', 'Livrée'),
            ('retournee', 'Retournée'),
        ],
        default='prep'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Livraison commande #{self.commande_id}"