from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("gravewright_accounts", "0006_admin_phrase_access"),
    ]

    operations = [
        migrations.CreateModel(
            name="KallistisPhraseCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_user_id", models.CharField(max_length=64, unique=True)),
                ("player_code", models.CharField(max_length=16, unique=True)),
                ("phrase_lookup_digest", models.CharField(editable=False, max_length=64, unique=True)),
                ("phrase_hash", models.CharField(editable=False, max_length=256)),
                ("revoked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="kallistis_phrase_credential", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
