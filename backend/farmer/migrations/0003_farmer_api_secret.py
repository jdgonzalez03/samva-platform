import secrets

from django.db import migrations, models

import farmer.models


def backfill_api_secrets(apps, schema_editor):
    Farmer = apps.get_model('farmer', 'Farmer')
    for farmer_row in Farmer.objects.filter(api_secret__isnull=True):
        farmer_row.api_secret = f"smv_{secrets.token_urlsafe(32)}"
        farmer_row.save(update_fields=['api_secret'])


class Migration(migrations.Migration):

    dependencies = [
        ('farmer', '0002_alter_farmer_address_alter_farmer_avatar_and_more'),
    ]

    # AddField con default callable + unique evaluaría el default una sola vez
    # para todas las filas existentes (violación de unicidad); por eso el campo
    # entra nullable, se rellena por fila y recién entonces adopta su forma final.
    operations = [
        migrations.AddField(
            model_name='farmer',
            name='api_secret',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.RunPython(backfill_api_secrets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='farmer',
            name='api_secret',
            field=models.CharField(
                default=farmer.models.generate_api_secret,
                editable=False,
                help_text='Token secreto para autenticar los sensores de campo del agricultor',
                max_length=64,
                unique=True,
                verbose_name='Secreto de API',
            ),
        ),
    ]
