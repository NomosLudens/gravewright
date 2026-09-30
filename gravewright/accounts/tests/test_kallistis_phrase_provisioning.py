import hashlib
import hmac
import json
import time

from django.conf import settings
from django.test import Client, TestCase, override_settings

from gravewright.accounts.models import KallistisIdentity, KallistisPhraseCredential, User
from gravewright.campaigns.models import Campaign, KallistisCampaignLink, Membership


SECRET = "test-only-kallistis-secret"
SOURCE_USER_ID = "11111111-1111-4111-8111-111111111111"
MESA_ID = "22222222-2222-4222-8222-222222222222"
PHRASE = "mi-thuvel"


@override_settings(KALLISTIS_VTT_SERVICE_SECRET=SECRET)
class KallistisPhraseProvisioningTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.player = User.objects.create_user(
            "player@example.test", "unused-password-123", name="Tony", role="participant"
        )
        self.player.set_unusable_password()
        self.player.save(update_fields=["password"])
        KallistisIdentity.objects.create(
            user=self.player, source_system="kallistis", source_user_id=SOURCE_USER_ID
        )
        self.owner = User.objects.create_user(
            "owner@example.test", "owner-password-123", name="Owner", role="owner"
        )
        self.campaign = Campaign.objects.create(owner=self.owner, name="AMIGOS ONLINE")
        KallistisCampaignLink.objects.create(
            source_mesa_id=MESA_ID, campaign=self.campaign
        )
        Membership.objects.create(
            campaign=self.campaign, user=self.player, role=Membership.Role.PLAYER
        )

    def payload(self, phrase=PHRASE):
        return {
            "schema": "kallistis.gravewright.player-phrase.v1",
            "source_user_id": SOURCE_USER_ID,
            "player_code": "JOGADOR-07",
            "source_mesa_id": MESA_ID,
            "campaign_id": str(self.campaign.pk),
            "phrase": phrase,
        }

    def signed_post(self, payload):
        body = json.dumps(payload)
        timestamp = str(int(time.time()))
        signature = hmac.new(
            SECRET.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
        ).hexdigest()
        return self.client.post(
            "/api/internal/kallistis/player-phrase",
            body,
            content_type="application/json",
            HTTP_X_KALLISTIS_TIMESTAMP=timestamp,
            HTTP_X_KALLISTIS_SIGNATURE="sha256=" + signature,
        )

    def test_one_piece_provisions_and_authenticates_player(self):
        response = self.signed_post(self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["source_user_id"], SOURCE_USER_ID)
        credential = KallistisPhraseCredential.objects.get(user=self.player)
        self.assertEqual(credential.player_code, "JOGADOR-07")
        self.assertNotIn(PHRASE, credential.phrase_hash)
        self.assertNotIn(PHRASE, credential.phrase_lookup_digest)

        self.client.get("/api/security/csrf")
        csrf_token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        login_response = self.client.post(
            "/api/auth/player-login",
            data={"phrase": PHRASE},
            content_type="application/json",
            HTTP_X_CSRF_TOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["account"]["name"], "Tony")
        self.assertTrue(self.client.get("/api/auth/session").json()["authenticated"])
        self.assertEqual(self.client.get("/api/home/player").status_code, 200)

    def test_non_velarim_piece_is_rejected_without_provisioning(self):
        response = self.signed_post(self.payload("short"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"valid": False, "error": "invalid_player_phrase"})
        self.assertFalse(KallistisPhraseCredential.objects.filter(user=self.player).exists())
