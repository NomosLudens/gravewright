from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

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

    @override_settings(
        CSRF_COOKIE_SECURE=True,
        CSRF_COOKIE_NAME="__Host-gravewright-csrf",
        SESSION_COOKIE_SECURE=True,
        CSRF_TRUSTED_ORIGINS=["https://testserver"],
    )
    def test_import_uses_runtime_csrf_contract(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.gm)
        csrf_response = client.get("/api/security/csrf", secure=True)
        self.assertEqual(csrf_response.status_code, 200)
        csrf_data = csrf_response.json()
        self.assertTrue(csrf_data["ready"])
        self.assertTrue(csrf_data["token"])
        self.assertTrue(client.cookies[settings.CSRF_COOKIE_NAME]["secure"])

        response = client.post(
            "/api/kallistis/import/preview",
            {
                "campaign_id": str(self.campaign.pk),
                "file": SimpleUploadedFile(
                    "kallistis.json",
                    json.dumps(payload()).encode(),
                    content_type="application/json",
                ),
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
            HTTP_X_CSRF_TOKEN=csrf_data["token"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])

        source = (
            Path(__file__).parent
            / "static"
            / "gravewright_actors"
            / "workspace.js"
        ).read_text()
        importer_source = source.split("function openKallistisImport", 1)[0]
        self.assertIn('fetch("/api/security/csrf"', importer_source)
        self.assertNotIn("document.cookie.match", importer_source)

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

    def test_import_confirm_returns_success_after_realtime_publish(self):
        import json
        from . import services

        self.client.force_login(self.gm)
        response = self.client.post(
            "/api/kallistis/import/confirm",
            data=json.dumps(
                {
                    "campaign_id": str(self.campaign.pk),
                    "membership_id": self.membership.pk,
                    "payload": payload(),
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(
            [row["name"] for row in services.state(self.campaign.pk, self.gm.pk)["actors"]],
            ["esquecido"],
        )

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
