from decimal import Decimal
import csv
from datetime import datetime

from django.conf import settings
from django.core import serializers
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum, F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, permission_required
from django.views import View
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .mixins import FournisseurRequiredMixin
from .models import Produit, Fournisseur, Commande, Livraison, LigneCommande
from .forms import FournisseurForm, ProduitForm, LivraisonForm, CommandeForm
from .decorators import fournisseur_required


# === Inscription basique (signup) ===
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


# === Pages produits / détails / commande simple ===
def index(request):
    produits = Produit.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'commandes/index.html', {"produits": produits})


def produit_detail(request, slug):
    produit = get_object_or_404(Produit, slug=slug, is_active=True)
    last_commande = Commande.objects.filter(produit=produit).exclude(statut='livree').order_by('-date_commande').first()
    return render(request, 'commandes/detail.html', {"produit": produit, "last_commande": last_commande})


def commander_produit(request, slug):
    produit = get_object_or_404(Produit, slug=slug, is_active=True)
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            quantite = form.cleaned_data['quantite']
            if quantite < produit.quantite_minimale:
                messages.error(request, f"La quantité minimale pour ce produit est {produit.quantite_minimale}.")
                return redirect('commandes:produit-detail', slug=produit.slug)
            commande = Commande.objects.create(produit=produit, quantite=quantite, client=request.user if request.user.is_authenticated else None)
            messages.success(request, f"Commande #{commande.id} créée.")
            return redirect('commandes:commande-detail', pk=commande.pk)
    else:
        form = CommandeForm(initial={'quantite': produit.quantite_minimale})
    return render(request, 'commandes/commander_form.html', {'produit': produit, 'form': form})


# === Listes et détails des commandes (admin / back-office) ===
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
        prix_unitaire = c.produit.prix if c.produit else Decimal('0')
        total = prix_unitaire * c.quantite
        fournisseur = c.produit.fournisseur.nom if c.produit and c.produit.fournisseur else ''
        writer.writerow([
            c.id,
            c.date_commande.isoformat(),
            c.produit.nom if c.produit else '',
            fournisseur,
            c.quantite,
            str(prix_unitaire),
            str(total),
            c.statut
        ])
    return response


# === Mise à jour / création d'une livraison (back-office) ===
def livraison_update(request, commande_pk):
    commande = get_object_or_404(Commande, pk=commande_pk)
    livraison, created = Livraison.objects.get_or_create(commande=commande)
    if request.method == 'POST':
        form = LivraisonForm(request.POST, instance=livraison)
        if form.is_valid():
            liv = form.save(commit=False)
            # timestamps automatiques et synchronisation du statut commande
            if liv.statut == 'en_transit' and not liv.assigned_at:
                liv.assigned_at = timezone.now()
                commande.statut = 'en_cours'
            if liv.statut == 'livree':
                if not liv.delivered_at:
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


# === CRUD Fournisseurs (admin-like) ===
def fournisseurs_list(request):
    fournisseurs = Fournisseur.objects.all().order_by('-id')
    return render(request, 'commandes/fournisseurs_list.html', {"fournisseurs": fournisseurs})


def fournisseur_create(request):
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


# === Panier (session) et checkout ===
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
    product_ids = [int(pk) for pk in cart.keys()] if cart else []
    produits = Produit.objects.filter(pk__in=product_ids) if product_ids else []
    items = []
    total = Decimal('0')
    for p in produits:
        q = int(cart.get(str(p.pk), 0))
        subtotal = (p.prix or Decimal('0')) * q
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
    items = []
    total_products = Decimal('0')
    for p in produits:
        q = int(cart.get(str(p.pk), 0))
        subtotal = (p.prix or Decimal('0')) * q
        total_products += subtotal
        items.append({'produit': p, 'qty': q, 'subtotal': subtotal})

    if request.method == 'POST':
        adresse = request.POST.get('adresse', '')
        methode = request.POST.get('methode', 'moto')
        description = request.POST.get('description', '')
        date_livraison_raw = request.POST.get('date_livraison')
        prix_raw = request.POST.get('montant', '')

        transport_costs = {
            'camion': Decimal('12000'),
            'moto': Decimal('4000'),
            'velo': Decimal('1500'),
        }
        livraison_prix = transport_costs.get(methode, transport_costs.get('moto'))

        try:
            montant = Decimal(prix_raw) if prix_raw else livraison_prix
        except Exception:
            montant = livraison_prix

        date_livraison = None
        if date_livraison_raw:
            try:
                date_livraison = datetime.fromisoformat(date_livraison_raw)
            except Exception:
                date_livraison = None

        try:
            with transaction.atomic():
                for pid, qty in cart.items():
                    p = get_object_or_404(Produit, pk=int(pid))
                    commande = Commande.objects.create(produit=p, quantite=int(qty), client=request.user if request.user.is_authenticated else None)
                    Livraison.objects.create(
                        commande=commande,
                        transport=methode,
                        adresse_livraison=adresse,
                        montant=montant,
                        description=description,
                        date_livraison=date_livraison,
                        statut='prep'
                    )
        except Exception as e:
            messages.error(request, f"Erreur lors du traitement de la commande : {e}")
            return redirect('commandes:cart_detail')

        total = total_products + Decimal(montant)

        try:
            user_email = getattr(request.user, 'email', None)
            if user_email:
                subject = 'Confirmation de votre commande'
                lines = [f'Bonjour {request.user.get_full_name() or request.user.username},', '', 'Merci pour votre commande. Voici le récapitulatif :', '']
                for it in items:
                    lines.append(f"- {it['produit'].nom} x{it['qty']} — {it['subtotal']}")
                lines.append('')
                lines.append(f"Total (produits) : {sum(it['subtotal'] for it in items)}")
                lines.append(f'Frais de livraison estimés : {montant}')
                lines.append(f'Total général : {total}')
                lines.append('')
                lines.append(f'Adresse de livraison : {adresse}')
                body = "\n".join(lines)
                send_mail(subject, body, getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@localhost'), [user_email], fail_silently=True)
        except Exception:
            pass

        return render(request, 'commandes/checkout_success.html', {
            'items': items,
            'total': total,
            'livraison_cost': montant,
            'total_produits': total_products,
            'adresse': adresse,
        })

    # Les coûts de transport sont récupérés depuis les settings
    transport_costs = getattr(settings, "TRANSPORT_COSTS", {
        'camion': Decimal('12000'),
        'moto': Decimal('4000'),
        'velo': Decimal('1500'),
    })

    return render(request, 'commandes/checkout.html', {
        'items': items,
        'total': total_products,
        'transport_costs': transport_costs
    })


# === Fournisseur / Dashboard / CRUD produit pour fournisseur ===

class DevenirFournisseurView(LoginRequiredMixin, CreateView):
    model = Fournisseur
    form_class = FournisseurForm
    template_name = "fournisseur/devenir.html"
    success_url = reverse_lazy("commandes:attente_approbation")

    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, "fournisseur_profile"):
            return redirect('commandes:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        # approved par défaut False -> attente admin
        return super().form_valid(form)


class AttenteApprobationView(LoginRequiredMixin, TemplateView):
    template_name = "fournisseur/attente.html"


class FournisseurDashboardView(FournisseurRequiredMixin, ListView):
    """
    Vue tableau de bord fournisseur utilisée par urls.py :
    path('fournisseur/dashboard/', views.FournisseurDashboardView.as_view(), name='dashboard')
    """
    template_name = "fournisseur/dashboard.html"
    context_object_name = "produits"

    def get_queryset(self):
        # Retourne uniquement les produits du fournisseur connecté
        return Produit.objects.filter(fournisseur=self.request.user.fournisseur_profile).order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.fournisseur_profile

        # KPIs
        total_produits = Produit.objects.filter(fournisseur=profile).count()
        qs_cmd = Commande.objects.filter(produit__fournisseur=profile)
        qs_cmd2 = Commande.objects.filter(lignes__produit__fournisseur=profile)
        commandes_total = (qs_cmd | qs_cmd2).distinct().count()

        qs_liv = Livraison.objects.filter(commande__produit__fournisseur=profile)
        qs_liv2 = Livraison.objects.filter(commande__lignes__produit__fournisseur=profile)
        livraisons_total = (qs_liv | qs_liv2).distinct().count()
        livraisons_en_attente = (qs_liv | qs_liv2).filter(statut__in=['prep', 'en_transit']).distinct().count()

        ventes_agregees = LigneCommande.objects.filter(produit__fournisseur=profile) \
            .aggregate(total_qte=Sum('quantite'))

        ctx.update({
            'kpi_total_produits': total_produits,
            'kpi_commandes_total': commandes_total,
            'kpi_livraisons_total': livraisons_total,
            'kpi_livraisons_en_attente': livraisons_en_attente,
            'kpi_total_qte_vendue': ventes_agregees.get('total_qte') or 0,
        })
        return ctx


class ProduitCreateView(FournisseurRequiredMixin, CreateView):
    model = Produit
    form_class = ProduitForm
    template_name = "fournisseur/produit_form.html"
    success_url = reverse_lazy('commandes:dashboard')

    def form_valid(self, form):
        form.instance.fournisseur = self.request.user.fournisseur_profile
        return super().form_valid(form)


class ProduitUpdateView(FournisseurRequiredMixin, UpdateView):
    model = Produit
    form_class = ProduitForm
    template_name = "fournisseur/produit_form.html"
    success_url = reverse_lazy('commandes:dashboard')

    def get_queryset(self):
        return Produit.objects.filter(fournisseur=self.request.user.fournisseur_profile)


class ProduitDeleteView(FournisseurRequiredMixin, DeleteView):
    model = Produit
    template_name = "fournisseur/produit_confirm_delete.html"
    success_url = reverse_lazy('commandes:dashboard')

    def get_queryset(self):
        # Restreindre la suppression aux produits du fournisseur connecté
        return Produit.objects.filter(fournisseur=self.request.user.fournisseur_profile)


class CommandesFournisseurListView(FournisseurRequiredMixin, ListView):
    template_name = "fournisseur/commandes.html"
    context_object_name = "commandes"

    def get_queryset(self):
        # Nous ne l'utilisons pas directement; nous préparons une liste dans get_context_data.
        return Commande.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.fournisseur_profile

        statut = self.request.GET.get('statut')
        start = self.request.GET.get('start')  # YYYY-MM-DD
        end = self.request.GET.get('end')      # YYYY-MM-DD

        qs1 = Commande.objects.filter(produit__fournisseur=profile)
        qs2 = Commande.objects.filter(lignes__produit__fournisseur=profile)
        commandes = (qs1 | qs2).distinct()

        if statut:
            commandes = commandes.filter(statut=statut)
        if start:
            try:
                dt = datetime.fromisoformat(start)
                commandes = commandes.filter(date_commande__date__gte=dt.date())
            except Exception:
                pass
        if end:
            try:
                dt = datetime.fromisoformat(end)
                commandes = commandes.filter(date_commande__date__lte=dt.date())
            except Exception:
                pass

        # Construire une liste adaptée au template: [{'commande': c, 'lignes': [{'produit':p,'quantite':q}, ...]}]
        data_list = []
        for c in commandes.order_by('-date_commande'):
            lignes = []
            # Lignes multi-produits du fournisseur
            for lc in c.lignes.filter(produit__fournisseur=profile):
                lignes.append({'produit': lc.produit, 'quantite': lc.quantite})
            # Cas commande directe sur un seul produit (champ commande.produit)
            if not lignes and c.produit and c.produit.fournisseur_id == profile.id:
                lignes.append({'produit': c.produit, 'quantite': c.quantite})
            data_list.append({'commande': c, 'lignes': lignes})

        ctx.update({
            'commandes': data_list,
            'filter_statut': statut or '',
            'filter_start': start or '',
            'filter_end': end or '',
            'statut_choices': Commande._meta.get_field('statut').choices,
        })
        return ctx


def mes_commandes(request):
    if not request.user.is_authenticated:
        return redirect('commandes:login')
    statut = request.GET.get('statut')
    qs = Commande.objects.filter(client=request.user).order_by('-date_commande')
    if statut:
        qs = qs.filter(statut=statut)
    statut_choices = Commande._meta.get_field('statut').choices
    return render(request, 'commandes/commandes_list.html', {'commandes': qs, 'statut_choices': statut_choices, 'mes': True})


class LivraisonFournisseurListView(FournisseurRequiredMixin, ListView):
    template_name = "fournisseur/livraisons.html"
    context_object_name = "livraisons"

    def get_queryset(self):
        profile = self.request.user.fournisseur_profile
        statut = self.request.GET.get('statut')
        start = self.request.GET.get('start')
        end = self.request.GET.get('end')

        qs = Livraison.objects.filter(commande__produit__fournisseur=profile)
        qs2 = Livraison.objects.filter(commande__lignes__produit__fournisseur=profile)
        livs = (qs | qs2).distinct()

        if statut:
            livs = livs.filter(statut=statut)
        if start:
            try:
                dt = datetime.fromisoformat(start)
                livs = livs.filter(commande__date_commande__date__gte=dt.date())
            except Exception:
                pass
        if end:
            try:
                dt = datetime.fromisoformat(end)
                livs = livs.filter(commande__date_commande__date__lte=dt.date())
            except Exception:
                pass

        return livs.order_by('-commande__date_commande')


class VentesFournisseurView(FournisseurRequiredMixin, ListView):
    """ Vue pour voir les ventes agrégées par produit pour un fournisseur """
    template_name = "fournisseur/ventes.html"
    context_object_name = "ventes"

    def get_queryset(self):
        profile = self.request.user.fournisseur_profile
        # Agréger les ventes à partir des lignes de commande
        return LigneCommande.objects.filter(produit__fournisseur=profile) \
            .values('produit__nom', 'produit__prix') \
            .annotate(total_qte=Sum('quantite')) \
            .annotate(total_montant=F('total_qte') * F('produit__prix')) \
            .order_by('-total_qte')


# Action fournisseur : marquer prête / en cours
class MarquerPreteView(FournisseurRequiredMixin, View):
    def post(self, request, pk):
        commande = get_object_or_404(Commande, pk=pk)
        profile = request.user.fournisseur_profile
        # Vérifie que le fournisseur a bien un produit dans cette commande
        is_related = commande.lignes.filter(produit__fournisseur=profile).exists()
        if not is_related:
            messages.error(request, "Action non autorisée.")
            return redirect('commandes:commandes-fournisseur')
        
        commande.statut = 'en_cours' # ou un autre statut pertinent
        commande.save()
        messages.success(request, f"La commande #{commande.id} a été marquée comme prête.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse_lazy('commandes:commandes-fournisseur')))


def dashboard_livraison(request):
    livraisons = Livraison.objects.all().order_by('-id')
    return render(request, "dashboard_livraison.html", {"livraisons": livraisons})


def modifier_statut_livraison(request, pk, statut):
    livraison = get_object_or_404(Livraison, pk=pk)
    livraison.update_status(statut)
    messages.success(request, f"Statut mis à jour : {statut}")
    return redirect("dashboard_livraison")