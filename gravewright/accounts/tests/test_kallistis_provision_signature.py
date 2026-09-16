import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from gravewright.accounts.views import kallistis_provision


SECRET = "test-only-kallistis-secret"
BODY = json.dumps({"schema": "kallistis.gravewright.mesa-provision.v1"})
RESULT = {
    "valid": True,
    "source_mesa_id": "11111111-1111-4111-8111-111111111111",
    "campaign_id": "44444444-4444-4444-8444-444444444444",
    "campaign_created": True,
    "campaign_reused": False,
    "members_created": 0,
    "members_updated": 0,
    "members_removed": 0,
}


def signed_headers(body, timestamp):
    signature = hmac.new(
        SECRET.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return {
        "HTTP_X_KALLISTIS_TIMESTAMP": str(timestamp),
        "HTTP_X_KALLISTIS_SIGNATURE": "sha256=" + signature,
    }


@override_settings(KALLISTIS_VTT_SERVICE_SECRET=SECRET)
class KallistisProvisionSignatureTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def post(self, headers=None):
        return self.factory.post(
            "/api/internal/kallistis/provision/mesa",
            BODY,
            content_type="application/json",
            **(headers or {}),
        )

    def test_missing_signature_is_rejected(self):
        response = kallistis_provision(self.post())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "signature_required")

    def test_invalid_signature_is_rejected(self):
        headers = signed_headers(BODY, int(time.time()))
        headers["HTTP_X_KALLISTIS_SIGNATURE"] = "sha256=" + "0" * 64
        response = kallistis_provision(self.post(headers))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "signature_invalid")

    def test_expired_signature_is_rejected(self):
        response = kallistis_provision(
            self.post(signed_headers(BODY, int(time.time()) - 61))
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "signature_expired")

    @patch("gravewright.accounts.views.provision", return_value=RESULT)
    def test_valid_signature_reaches_provisioner(self, provision):
        timestamp = int(time.time())
        response = kallistis_provision(
            self.post(signed_headers(BODY, timestamp))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), RESULT)
        provision.assert_called_once_with(json.loads(BODY))
