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
    images = models.ImageField(upload_to='produits/', blank=True, null=True)
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