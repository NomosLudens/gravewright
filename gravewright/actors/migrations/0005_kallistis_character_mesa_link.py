from django.db import migrations, models


def backfill_mesa_ids(apps, schema_editor):
    CharacterLink = apps.get_model("gravewright_actors", "KallistisCharacterLink")
    CampaignLink = apps.get_model("gravewright_campaigns", "KallistisCampaignLink")
    links = {
        str(row.campaign_id): str(row.source_mesa_id)
        for row in CampaignLink.objects.all().only("campaign_id", "source_mesa_id")
    }
    for row in CharacterLink.objects.select_related("actor").all().iterator():
        mesa_id = links.get(str(row.actor.campaign_id), "")
        if mesa_id:
            CharacterLink.objects.filter(pk=row.pk).update(source_mesa_id=mesa_id)


class Migration(migrations.Migration):
    dependencies = [
        ("gravewright_actors", "0004_kallistischaracterlink"),
        ("gravewright_campaigns", "0005_kallistiscampaignlink_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="kallistischaracterlink",
            name="source_mesa_id",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AlterField(
            model_name="kallistischaracterlink",
            name="kallistis_character_id",
            field=models.CharField(max_length=128),
        ),
        migrations.RunPython(backfill_mesa_ids, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="kallistischaracterlink",
            constraint=models.UniqueConstraint(
                fields=("kallistis_character_id", "source_mesa_id"),
                name="actors_kallistis_character_mesa_link",
            ),
        ),
    ]
