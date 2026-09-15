from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [("gravewright_accounts", "0003_userpreference_locale")]
    operations = [
        migrations.CreateModel(
            name="KallistisIdentity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_system", models.CharField(default="kallistis", max_length=32)),
                ("source_user_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="kallistis_identity", to="gravewright_accounts.user")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("source_system", "source_user_id"), name="accounts_kallistis_source_identity"),
                ],
            },
        ),
    ]
