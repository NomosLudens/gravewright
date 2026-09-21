import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import Client, TestCase, override_settings

from gravewright.accounts.models import KallistisIdentity, User


READ_URL = "https://kallistis.example.test/api/internal/vtt/characters/read"
SECRET = "test-only-kallistis-secret"
SOURCE_USER_ID = "source-user-123"
CHARACTER_ID = "character-123"
PAYLOAD = {
    "valid": True,
    "character": {
        "id": CHARACTER_ID,
        "kallistis": {
            "manifestacao_pessoal": "A manifestação real",
            "fulgor_current": 7,
            "capability_manifestation_descriptions": {"fogo": "Chama"},
        },
    },
}


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body


@override_settings(
    KALLISTIS_VTT_CHARACTER_READ_URL=READ_URL,
    KALLISTIS_VTT_SERVICE_SECRET=SECRET,
)
class KallistisCharacterReadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            name="KALLISTIS Shadow", email="shadow@example.test"
        )
        self.identity = KallistisIdentity.objects.create(
            user=self.user, source_user_id=SOURCE_USER_ID
        )
        self.client.force_login(self.user)

    def remote_ok(self, request, **kwargs):
        self.assertEqual(request.full_url, READ_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer " + SECRET)
        self.assertEqual(request.get_header("User-agent"), "Gravewright-KALLISTIS-Bridge/1")
        body = json.loads(request.data)
        self.assertEqual(body["source_user_id"], SOURCE_USER_ID)
        self.assertEqual(body["characterId"], CHARACTER_ID)
        return FakeResponse(json.dumps(PAYLOAD).encode())

    @patch("gravewright.accounts.kallistis.urlopen")
    def test_returns_minimal_projection_from_identity(self, urlopen):
        urlopen.side_effect = self.remote_ok
        before = KallistisIdentity.objects.count()

        response = self.client.get(
            f"/api/kallistis/characters/{CHARACTER_ID}?source_user_id=attacker"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"character": PAYLOAD["character"]})
        self.assertNotIn("ownerUserId", response.json()["character"])
        self.assertEqual(KallistisIdentity.objects.count(), before)
        urlopen.assert_called_once()

    def test_identity_is_required(self):
        self.identity.delete()
        with patch("gravewright.accounts.kallistis.urlopen") as urlopen:
            response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "kallistis_identity_required")
        urlopen.assert_not_called()

    @patch("gravewright.accounts.kallistis.urlopen")
    def test_remote_404_is_safe_not_found(self, urlopen):
        urlopen.side_effect = HTTPError(READ_URL, 404, "not found", {}, None)
        response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "character_not_found")

    @patch("gravewright.accounts.kallistis.urlopen", side_effect=URLError("offline"))
    def test_remote_unavailable_is_safe_failure(self, urlopen):
        response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "character_read_failure")

    @patch("gravewright.accounts.kallistis.urlopen")
    def test_invalid_json_is_safe_failure(self, urlopen):
        urlopen.return_value = FakeResponse(b"not-json")
        response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "character_read_failure")

    def test_missing_secret_or_url_is_safe_failure(self):
        with override_settings(KALLISTIS_VTT_SERVICE_SECRET=""):
            response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "character_read_not_configured")
        with override_settings(KALLISTIS_VTT_CHARACTER_READ_URL=""):
            response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 503)

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(f"/api/kallistis/characters/{CHARACTER_ID}")
        self.assertEqual(response.status_code, 401)
