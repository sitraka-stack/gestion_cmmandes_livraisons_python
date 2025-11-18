from django.db import migrations
from django.contrib.auth import get_user_model

def create_users_for_fournisseurs(apps, schema_editor):
    Fournisseur = apps.get_model('commandes', 'Fournisseur')
    User = get_user_model()
    for f in Fournisseur.objects.filter(user__isnull=True):
        base = (f.email.split('@')[0] if f.email else f'nf_{f.pk}')
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            i += 1
            username = f"{base}{i}"
        user = User.objects.create(username=username, email=(f.email or ''))
        user.set_unusable_password()
        user.is_active = False
        user.save()
        f.user_id = user.pk
        f.save()

def reverse_func(apps, schema_editor):
    # ne pas supprimer les users automatiquement
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('commandes', '0006_fournisseur_approved_fournisseur_bank_account_and_more'),
    ]

    operations = [
        migrations.RunPython(create_users_for_fournisseurs, reverse_func),
    ]