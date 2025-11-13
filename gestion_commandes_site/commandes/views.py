from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.contrib import messages
from django.utils import timezone
import csv
from django.core import serializers
from decimal import Decimal
from datetime import datetime

from .models import Produit, Fournisseur, Commande, LigneCommande, Livraison
from .forms import FournisseurForm, LivraisonForm, CommandeForm
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

#Fonction pour le login 
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('commandes:index')
    else:
        form = UserCreationForm()
    return render(request, 'commandes/signup.html', {'form': form})






# Page d'accueil produits (index)
def index(request):
    produits = Produit.objects.all()
    return render(request, 'commandes/index.html', context={"produits": produits})

# Détail produit
def produit_detail(request, slug):
    produit = get_object_or_404(Produit, slug=slug)
    # rechercher la commande la plus récente non livrée pour afficher "Livrer" si besoin
    last_commande = Commande.objects.filter(produit=produit).exclude(statut='livree').order_by('-date_commande').first()
    return render(request, 'commandes/detail.html', context={"produit": produit, "last_commande": last_commande})

# Commander un produit (formulaire simple quantité)
def commander_produit(request, slug):
    produit = get_object_or_404(Produit, slug=slug)
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            quantite = form.cleaned_data['quantite']
            if quantite < produit.quantite_minimale:
                messages.error(request, f"La quantité minimale pour ce produit est {produit.quantite_minimale}.")
                return redirect('commandes:produit-detail', slug=produit.slug)
            commande = Commande.objects.create(produit=produit, quantite=quantite)
            messages.success(request, f"Commande #{commande.id} créée.")
            return redirect('commandes:commande-detail', pk=commande.pk)
    else:
        form = CommandeForm(initial={'quantite': produit.quantite_minimale})
    return render(request, 'commandes/commander_form.html', {'produit': produit, 'form': form})

# Commandes list + detail (existing)
def commandes_list(request):
    qs = Commande.objects.select_related('produit__fournisseur').all().order_by('-date_commande')
    statut = request.GET.get('statut')
    q = request.GET.get('q')
    if statut:
        qs = qs.filter(statut=statut)
    if q:
        if q.isdigit():
            qs = qs.filter(id=int(q))
        else:
            qs = qs.filter(produit__nom__icontains=q)
    # passer les choices au template si besoin
    statut_choices = Commande._meta.get_field('statut').choices
    return render(request, 'commandes/commandes_list.html', {'commandes': qs, 'statut_choices': statut_choices})

def commande_detail(request, pk):
    commande = get_object_or_404(Commande, pk=pk)
    livraison = getattr(commande, 'livraison', None)
    return render(request, 'commandes/commande_detail.html', {'commande': commande, 'livraison': livraison})

def commandes_json(request):
    qs = Commande.objects.all()
    json_data = serializers.serialize('json', qs, use_natural_foreign_keys=True)
    return HttpResponse(json_data, content_type='application/json; charset=utf-8')

def export_commandes_csv(request):
    qs = Commande.objects.select_related('produit__fournisseur').all().order_by('-date_commande')
    statut = request.GET.get('statut')
    if statut:
        qs = qs.filter(statut=statut)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="commandes.csv"'
    writer = csv.writer(response)
    writer.writerow(['id', 'date_commande', 'produit', 'fournisseur', 'quantite', 'prix_unitaire', 'total', 'statut'])
    for c in qs:
        prix_unitaire = c.produit.prix
        total = prix_unitaire * c.quantite
        fournisseur = c.produit.fournisseur.nom if c.produit.fournisseur else ''
        writer.writerow([c.id, c.date_commande.isoformat(), c.produit.nom, fournisseur, c.quantite, str(prix_unitaire), str(total), c.statut])
    return response

# Livraisons : création / mise à jour du détail de livraison
def livraison_update(request, commande_pk):
    commande = get_object_or_404(Commande, pk=commande_pk)
    livraison, created = Livraison.objects.get_or_create(commande=commande)
    if request.method == 'POST':
        form = LivraisonForm(request.POST, instance=livraison)
        if form.is_valid():
            liv = form.save(commit=False)
            # timestamps automatiques
            if liv.statut == 'en_transit' and not liv.assigned_at:
                liv.assigned_at = timezone.now()
                commande.statut = 'en_cours'
            if liv.statut == 'livree':
                liv.delivered_at = timezone.now()
                commande.statut = 'livree'
            if liv.statut == 'prep':
                commande.statut = 'en_attente'
            if liv.statut == 'retournee':
                commande.statut = 'annulee'
            liv.save()
            commande.save()
            messages.success(request, "Statut / infos de livraison mises à jour.")
            return redirect('commandes:commande-detail', pk=commande.pk)
    else:
        form = LivraisonForm(instance=livraison)
    return render(request, 'commandes/livraison_form.html', {'form': form, 'commande': commande})



def fournisseurs_list(request):
    from .models import Fournisseur
    fournisseurs = Fournisseur.objects.all().order_by('-id')
    return render(request, 'commandes/fournisseurs_list.html', context={"fournisseurs": fournisseurs})


def fournisseur_create(request):
    from .models import Fournisseur
    from .forms import FournisseurForm
    from django.shortcuts import redirect, render
    from django.contrib import messages

    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fournisseur ajouté.")
            return redirect('commandes:fournisseurs-list')
    else:
        form = FournisseurForm()
    return render(request, 'commandes/fournisseur_form.html', {'form': form, 'action': 'Ajouter'})



def fournisseur_edit(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, "Fournisseur mis à jour.")
            return redirect('commandes:fournisseurs-list')
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, 'commandes/fournisseur_form.html', {'form': form, 'action': 'Éditer'})

def fournisseur_delete(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == 'POST':
        fournisseur.delete()
        messages.success(request, "Fournisseur supprimé.")
        return redirect('commandes:fournisseurs-list')
    return render(request, 'commandes/fournisseur_confirm_delete.html', {'fournisseur': fournisseur})



    #Les 4 fonction ci dessous sont pour ajouter/voir/retirer/checkout du panier des produits séléctionner 
    # ...existing code...
def _get_cart(session):
    return session.setdefault('cart', {})

def add_to_cart(request, product_id):
    qty = int(request.POST.get('qty', 1))
    cart = _get_cart(request.session)
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    request.session.modified = True
    return redirect('commandes:cart_detail')

def remove_from_cart(request, product_id):
    cart = _get_cart(request.session)
    cart.pop(str(product_id), None)
    request.session.modified = True
    return redirect('commandes:cart_detail')

def cart_detail(request):
    cart = _get_cart(request.session)
    product_ids = [int(pk) for pk in cart.keys()]
    produits = Produit.objects.filter(pk__in=product_ids)
    items = []
    total = 0
    for p in produits:
        q = cart.get(str(p.pk), 0)
        subtotal = (p.prix or 0) * q
        total += subtotal
        items.append({'produit': p, 'qty': q, 'subtotal': subtotal})
    return render(request, 'commandes/cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    cart = _get_cart(request.session)
    if not cart:
        return redirect('commandes:cart_detail')

    if request.method == 'POST':
        adresse = request.POST.get('adresse', '')
        methode = request.POST.get('methode', 'moto')  # ex: 'moto', 'pied', 'express'
        description = request.POST.get('description', '')
        date_livraison_raw = request.POST.get('date_livraison')  # format 'YYYY-MM-DDTHH:MM' (datetime-local)
        prix_raw = request.POST.get('montant', '')  # si tu fournis un montant calculé côté client

        # calcul simple du montant livraison si non fourni
        livraison_prix = {'moto': 4000, 'pied': 1000, 'express': 7000}.get(methode, 4000)
        try:
            if prix_raw:
                montant = Decimal(prix_raw)
            else:
                montant = Decimal(livraison_prix)
        except Exception:
            montant = Decimal(livraison_prix)

        # parse date_livraison si fournie
        date_livraison = None
        if date_livraison_raw:
            try:
                # datetime.fromisoformat accepte 'YYYY-MM-DDTHH:MM' et 'YYYY-MM-DDTHH:MM:SS'
                date_livraison = datetime.fromisoformat(date_livraison_raw)
                # rendre aware si tu utilises timezone-aware datetimes
                # date_livraison = timezone.make_aware(date_livraison)
            except Exception:
                date_livraison = None

        # créer commandes + livraison dans une transaction
        try:
            with transaction.atomic():
                for pid, qty in cart.items():
                    p = get_object_or_404(Produit, pk=int(pid))
                    # créer la commande
                    commande = Commande.objects.create(
                        produit=p,
                        quantite=qty,
                    )
                    # créer la livraison liée — utiliser les noms de champs réels du modèle
                    Livraison.objects.create(
                        commande=commande,
                        transport=methode,                # champ 'transport' dans ton modèle
                        adresse_livraison=adresse,        # champ 'adresse_livraison'
                        montant=montant,
                        description=description,
                        date_livraison=date_livraison,
                        statut='prep'
                    )
        except Exception as e:
            messages.error(request, "Erreur lors du traitement de la commande : %s" % e)
            return redirect('commandes:cart_detail')

        # vider le panier
        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, "Commande créée avec succès. Vous recevrez les informations de livraison bientôt.")
        return render(request, 'commandes/checkout_success.html')

    # GET -> afficher résumé et choix méthode
    product_ids = [int(pk) for pk in cart.keys()]
    produits = Produit.objects.filter(pk__in=product_ids)
    total = sum((p.prix or 0) * cart.get(str(p.pk), 0) for p in produits)
    return render(request, 'commandes/checkout.html', {'total': total})


def _get_cart(session):
    return session.setdefault('cart', {})

def add_to_cart(request, product_id):
    # accepte POST (formulaire) ou GET (simple click)
    qty = int(request.POST.get('qty', 1)) if request.method == 'POST' else 1
    cart = _get_cart(request.session)
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    request.session.modified = True
    return redirect('commandes:cart_detail')

def remove_from_cart(request, product_id):
    cart = _get_cart(request.session)
    cart.pop(str(product_id), None)
    request.session.modified = True
    return redirect('commandes:cart_detail')

def cart_detail(request):
    cart = _get_cart(request.session)
    product_ids = [int(pk) for pk in cart.keys()] if cart else []
    produits = Produit.objects.filter(pk__in=product_ids)
    items = []
    total = 0
    for p in produits:
        q = cart.get(str(p.pk), 0)
        subtotal = (p.prix or 0) * q
        total += subtotal
        items.append({'produit': p, 'qty': q, 'subtotal': subtotal})
    return render(request, 'commandes/cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    cart = _get_cart(request.session)
    if not cart:
        return redirect('commandes:cart_detail')
    product_ids = [int(pk) for pk in cart.keys()]
    produits = Produit.objects.filter(pk__in=product_ids)
    total_produits = sum((p.prix or 0) * cart.get(str(p.pk), 0) for p in produits)

    if request.method == 'POST':
        adresse = request.POST.get('adresse', '')
        methode = request.POST.get('methode', 'moto')
        prix_livraison = {'moto': 4000, 'pied': 1000, 'express': 7000}.get(methode, 4000)
        # Exemple simple : créer une commande par produit
        for pid, qty in cart.items():
            p = get_object_or_404(Produit, pk=int(pid))
            commande = Commande.objects.create(produit=p, quantite=qty)
            Livraison.objects.create(commande=commande, adresse=adresse, methode=methode, montant=prix_livraison)
        request.session['cart'] = {}
        request.session.modified = True
        return render(request, 'commandes/checkout_success.html', {'total': total_produits + prix_livraison})
    return render(request, 'commandes/checkout.html', {'produits': produits, 'total': total_produits})