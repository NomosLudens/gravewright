import hashlib
import hmac
import json
import time

from django.test import RequestFactory, TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.accounts.views import kallistis_campaign_link, kallistis_campaign_list
from gravewright.campaigns.models import Campaign, KallistisCampaignLink, Membership


SECRET = "test-only-kallistis-secret"
MESA_ID = "11111111-1111-4111-8111-111111111111"
OTHER_MESA_ID = "22222222-2222-4222-8222-222222222222"


def signed_headers(body):
    timestamp = int(time.time())
    signature = hmac.new(
        SECRET.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return {
        "HTTP_X_KALLISTIS_TIMESTAMP": str(timestamp),
        "HTTP_X_KALLISTIS_SIGNATURE": "sha256=" + signature,
    }


@override_settings(KALLISTIS_VTT_SERVICE_SECRET=SECRET)
class KallistisCampaignMappingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(
            "owner@example.test", "owner-password-123", name="Owner", role="owner"
        )
        self.available = Campaign.objects.create(owner=self.owner, name="Existing Campaign")
        self.already_linked = Campaign.objects.create(owner=self.owner, name="Already Linked")
        KallistisCampaignLink.objects.create(
            source_mesa_id=OTHER_MESA_ID, campaign=self.already_linked
        )
        Membership.objects.create(campaign=self.available, user=self.owner, role="gm")

    def post(self, path, payload):
        body = json.dumps(payload)
        return self.factory.post(
            path,
            body,
            content_type="application/json",
            **signed_headers(body),
        )

    def test_list_returns_only_unlinked_campaigns(self):
        response = kallistis_campaign_list(self.post(
            "/api/internal/kallistis/campaigns/list",
            {"schema": "kallistis.gravewright.campaign-list.v1", "source_system": "kallistis"},
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["campaigns"], [{"id": str(self.available.pk), "name": "Existing Campaign"}])

    def test_link_is_idempotent_and_does_not_create_memberships(self):
        payload = {
            "schema": "kallistis.gravewright.campaign-link.v1",
            "source_system": "kallistis",
            "source_mesa_id": MESA_ID,
            "campaign_id": str(self.available.pk),
        }
        first = kallistis_campaign_link(self.post("/api/internal/kallistis/campaigns/link", payload))
        second = kallistis_campaign_link(self.post("/api/internal/kallistis/campaigns/link", payload))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(json.loads(first.content)["mapping_created"])
        self.assertFalse(json.loads(second.content)["mapping_created"])
        self.assertEqual(KallistisCampaignLink.objects.count(), 2)
        self.assertEqual(Membership.objects.count(), 1)

    def test_link_rejects_campaign_already_linked_elsewhere(self):
        payload = {
            "schema": "kallistis.gravewright.campaign-link.v1",
            "source_system": "kallistis",
            "source_mesa_id": MESA_ID,
            "campaign_id": str(self.already_linked.pk),
        }
        response = kallistis_campaign_link(self.post("/api/internal/kallistis/campaigns/link", payload))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.content)["error"], "vtt_campaign_already_mapped")

    def test_missing_signature_is_rejected(self):
        request = self.factory.post(
            "/api/internal/kallistis/campaigns/list",
            json.dumps({"schema": "kallistis.gravewright.campaign-list.v1", "source_system": "kallistis"}),
            content_type="application/json",
        )
        self.assertEqual(kallistis_campaign_list(request).status_code, 401)
