from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gravewright_campaigns", "0004_kallistiscampaignlink")]

    operations = [
        migrations.AddField(
            model_name="kallistiscampaignlink",
            name="source_mesa_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
