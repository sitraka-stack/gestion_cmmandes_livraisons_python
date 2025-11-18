from django import forms
from .models import Fournisseur, Livraison



class CommandeForm(forms.Form):
    quantite = forms.IntegerField(min_value=1, label="Quantité", widget=forms.NumberInput(attrs={'class': 'form-control'}))

class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ['transport', 'adresse_livraison', 'montant', 'description', 'date_livraison', 'statut']
        widgets = {
            'transport': forms.Select(attrs={'class': 'form-control'}),
            'adresse_livraison': forms.TextInput(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_livraison': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }



        
from .models import Fournisseur, Produit

class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom', 'email', 'telephone', 'adresse', 'ville', 'bank_account', 'commission_rate']
        widgets = {
            'commission_rate': forms.NumberInput(attrs={'step': '0.01'}),
        }



class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['nom', 'slug', 'images', 'description', 'prix', 'quantite_minimale', 'is_active']