from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gravewright_accounts", "0005_kallistisplayeraccess"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="kallistisplayeraccess",
            name="accounts_player_access_code_prefix",
        ),
        migrations.AddConstraint(
            model_name="kallistisplayeraccess",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(player_code__startswith="JOGADOR-")
                    | models.Q(player_code__startswith="ADMIN-")
                ),
                name="accounts_player_access_code_prefix",
            ),
        ),
    ]
