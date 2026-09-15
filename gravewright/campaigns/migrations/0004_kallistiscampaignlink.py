from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [("gravewright_campaigns", "0003_onboarding_streamerlink_and_more")]
    operations = [
        migrations.CreateModel(
            name="KallistisCampaignLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_system", models.CharField(default="kallistis", max_length=32)),
                ("source_mesa_id", models.UUIDField(unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("campaign", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="kallistis_link", to="gravewright_campaigns.campaign")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("source_system", "source_mesa_id"), name="campaigns_kallistis_mesa_link"),
                ],
            },
        ),
    ]
