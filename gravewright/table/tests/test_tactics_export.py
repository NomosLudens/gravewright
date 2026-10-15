from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    ROOT_URLCONF="config.runner_urls",
)
class TacticsExportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "tactics-gm@example.test", "password-12345", name="GM", role="owner"
        )
        self.player = User.objects.create_user(
            "tactics-player@example.test", "password-12345", name="Player"
        )
        self.campaign = Campaign.objects.create(owner=self.owner, name="Tactics")
        Membership.objects.create(campaign=self.campaign, user=self.owner, role="gm")

    def test_export_requires_campaign_membership_and_keeps_campaign_in_browser_url(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        export_root = Path(root.name)
        (export_root / "index.html").write_text(
            "<script>globalThis.tactics = true;</script>", encoding="utf-8"
        )
        (export_root / "game.wasm").write_bytes(b"wasm")

        path = f"/game/{self.campaign.pk}/tactics/"
        self.assertRedirects(self.client.get(path), "/login", fetch_redirect_response=False)
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(path).status_code, 404)

        self.client.force_login(self.owner)
        with patch("gravewright.table.tactics_export.EXPORT_ROOT", export_root):
            redirect = self.client.get(path)
            self.assertEqual(redirect.status_code, 302)
            self.assertEqual(
                redirect["Location"], f"{path}?campaign={self.campaign.pk}"
            )
            response = self.client.get(redirect["Location"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                b"".join(response.streaming_content),
                b"<script>globalThis.tactics = true;</script>",
            )
            self.assertIn("'sha256-", response["Content-Security-Policy"])
            asset = self.client.get(f"/game/{self.campaign.pk}/tactics/game.wasm")
            self.assertEqual(asset.status_code, 200)
            self.assertEqual(asset["Content-Type"], "application/wasm")

    def test_export_rejects_paths_outside_the_export_root(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.client.force_login(self.owner)
        with patch("gravewright.table.tactics_export.EXPORT_ROOT", Path(root.name)):
            response = self.client.get(
                f"/game/{self.campaign.pk}/tactics/../secret.txt"
            )
        self.assertEqual(response.status_code, 404)
