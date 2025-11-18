from django.db import models
from django.conf import settings
from django.utils import timezone

# Utilise la référence configurée vers le modèle User
USER_MODEL = settings.AUTH_USER_MODEL

class Fournisseur(models.Model):
    # Liaison avec l'utilisateur Django
    user = models.OneToOneField(USER_MODEL, on_delete=models.CASCADE, related_name='fournisseur_profile')
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=15, blank=True)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    approved = models.BooleanField(default=False, help_text="Validé par l'admin pour vendre")
    created_at = models.DateTimeField(auto_now_add=True)

    # Champs facturation / commission
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Pourcentage de commission (%) prélevé par la plateforme"
    )
    bank_account = models.CharField(max_length=255, blank=True, help_text="Détails bancaires pour versement")

    def __str__(self):
        return self.nom or getattr(self.user, "get_full_name", lambda: "")() or getattr(self.user, "username", "")

class Produit(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(max_length=128, unique=True)
    images = models.ImageField(upload_to="produits/", blank=True, null=True)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name='produits')
    quantite_minimale = models.PositiveIntegerField(default=1, help_text="Quantité minimale de commande")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom} (Min: {self.quantite_minimale})"

class Commande(models.Model):
    # Nouveau: lien vers l'utilisateur qui a passé la commande
    client = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, null=True, blank=True)
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

    class Meta:
        ordering = ['-date_commande']

    def __str__(self):
        user_part = f" pour {self.client.username}" if self.client else ""
        return f"Commande {self.id}{user_part} - {self.produit.nom if self.produit else '—'}"

class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
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

    # Tarifs par type (en Ariary ou autre devise selon ton usage)
    TARIFS = {
        'moto': 4000,
        'voiture': 12000,
        'a_pied': 1500,
        'trottinette': 2000,
    }

    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='livraison')
    transport = models.CharField(max_length=30, choices=TRANSPORT_CHOICES, blank=True, null=True)
    adresse_livraison = models.CharField(max_length=255, blank=True)
    montant = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    date_prevue = models.DateTimeField(null=True, blank=True)
    date_effective = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

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

    class Meta:
        verbose_name = "Livraison"
        verbose_name_plural = "Livraisons"
        ordering = ['-date_prevue']

    def set_tarif(self):
        """Définit le montant en fonction du type de transport."""
        if self.transport:
            tarif = self.TARIFS.get(self.transport, 0)
            self.montant = tarif

    def update_status(self, new_status):
        """Gère automatiquement les dates selon le statut et enregistre."""
        self.statut = new_status

        if new_status == "en_transit" and not self.assigned_at:
            self.assigned_at = timezone.now()

        if new_status == "livree" and not self.delivered_at:
            self.delivered_at = timezone.now()
            # date_effective peut aussi être définie ici
            if not self.date_effective:
                self.date_effective = timezone.now()

        self.save()

    def save(self, *args, **kwargs):
        # Si montant non renseigné mais transport renseigné, calcule le tarif
        if (not self.montant or self.montant == 0) and self.transport:
            self.set_tarif()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Livraison commande #{self.commande.id}"