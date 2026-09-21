from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership

from .kallistis_import import (
    KallistisImportError,
    import_character,
    preview,
    validate_payload,
)
from .models import Actor, KallistisCharacterLink


def payload(**overrides):
    value = {
        "schema": "kallistis.gravewright.character",
        "schema_version": 1,
        "export_mode": "manual_runtime_snapshot",
        "source_state": "submitted",
        "canonical": False,
        "mesa": {"id": "mesa-1", "name": "AMIGOS ONLINE"},
        "player": {
            "kallistis_user_id": None,
            "display_name": "Jogador",
            "email": None,
        },
        "character": {
            "kallistis_character_id": "cmu657xqwme2tl",
            "name": "esquecido",
            "published_version": None,
            "snapshot": {
                "nome": "esquecido",
                "trilhas": [{"oficio": "Guardião", "marco": 1}],
                "trilhaAtiva": 0,
                "atributosBase": {
                    "Corpo": 2,
                    "Agilidade": 1,
                    "Intelecto": 1,
                    "Presença": 1,
                    "Vontade": 1,
                    "Sintonia": 0,
                },
                "descricao": "Snapshot de runtime",
            },
        },
    }
    value.update(overrides)
    return value


class KallistisImportTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user(
            "gm@example.test", "gm-password-123", name="Mestre", role="owner"
        )
        self.player = User.objects.create_user(
            "player@example.test", "player-password-123", name="Jogador", role="participant"
        )
        self.other = User.objects.create_user(
            "other@example.test", "other-password-123", name="Outro", role="participant"
        )
        self.campaign = Campaign.objects.create(owner=self.gm, name="Gate 03B Mesa KALLISTIS")
        self.other_campaign = Campaign.objects.create(owner=self.gm, name="Outra campanha")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        self.membership = Membership.objects.create(
            campaign=self.campaign, user=self.player, role="player"
        )
        Membership.objects.create(campaign=self.other_campaign, user=self.gm, role="gm")

    def test_manual_runtime_snapshot_is_accepted_with_null_email(self):
        parsed = validate_payload(payload())
        result = preview(parsed)
        self.assertEqual(result["export_mode"], "manual_runtime_snapshot")
        self.assertFalse(result["canonical"])
        self.assertFalse(result["player"]["email_present"])
        self.assertEqual(result["character_name"], "esquecido")

    def test_invalid_schema_and_snapshot_are_rejected(self):
        with self.assertRaisesRegex(KallistisImportError, "invalid_schema"):
            validate_payload({**payload(), "schema": "other"})
        invalid = deepcopy(payload())
        invalid["character"]["snapshot"] = {"nome": "incompleta"}
        with self.assertRaisesRegex(KallistisImportError, "invalid_snapshot"):
            validate_payload(invalid)

    def test_import_creates_actor_link_and_selected_player_control(self):
        before_campaigns = Campaign.objects.count()
        before_users = User.objects.count()
        before_memberships = Membership.objects.count()
        result = import_character(
            self.gm.pk, self.campaign.pk, self.membership.pk, payload()
        )
        actor = Actor.objects.get(pk=result["actor_id"])
        link = KallistisCharacterLink.objects.get(actor=actor)
        self.assertEqual(actor.campaign_id, self.campaign.pk)
        self.assertEqual(actor.permissions, {str(self.player.pk): "owner"})
        self.assertEqual(link.kallistis_character_id, "cmu657xqwme2tl")
        self.assertEqual(Campaign.objects.count(), before_campaigns)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Membership.objects.count(), before_memberships)

    def test_duplicate_character_does_not_create_second_actor(self):
        import_character(self.gm.pk, self.campaign.pk, self.membership.pk, payload())
        before = Actor.objects.count()
        with self.assertRaisesRegex(KallistisImportError, "already_imported"):
            import_character(self.gm.pk, self.campaign.pk, self.membership.pk, payload())
        self.assertEqual(Actor.objects.count(), before)

    def test_non_gm_and_missing_campaign_player_are_denied(self):
        with self.assertRaisesRegex(KallistisImportError, "unauthorized"):
            import_character(self.player.pk, self.campaign.pk, self.membership.pk, payload())
        outsider_membership = Membership.objects.create(
            campaign=self.other_campaign, user=self.other, role="player"
        )
        with self.assertRaisesRegex(KallistisImportError, "player_not_in_campaign"):
            import_character(self.gm.pk, self.campaign.pk, outsider_membership.pk, payload())

    def test_transaction_rolls_back_actor_when_link_creation_fails(self):
        with patch(
            "gravewright.actors.kallistis_import.KallistisCharacterLink.objects.create",
            side_effect=RuntimeError("link failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "link failure"):
                import_character(self.gm.pk, self.campaign.pk, self.membership.pk, payload())
        self.assertEqual(Actor.objects.count(), 0)
        self.assertEqual(KallistisCharacterLink.objects.count(), 0)
