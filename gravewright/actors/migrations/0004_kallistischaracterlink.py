from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("gravewright_actors", "0003_actor_type")]

    operations = [
        migrations.CreateModel(
            name="KallistisCharacterLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("kallistis_character_id", models.CharField(max_length=128, unique=True)),
                ("source_schema_version", models.PositiveIntegerField(default=1)),
                ("source_state", models.CharField(max_length=32)),
                ("canonical", models.BooleanField(default=False)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kallistis_link",
                        to="gravewright_actors.actor",
                    ),
                ),
            ],
        ),
    ]
