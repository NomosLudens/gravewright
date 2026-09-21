from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import KallistisPlayerAccess, User
from gravewright.accounts.services import kallistis_phrase_digest


FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PHRASE = "unit-test-access-phrase"


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class KallistisPlayerAccessTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.get("/api/security/csrf")
        self.owner = User.objects.create_user(
            name="Mestre", email="gm@example.test", password="owner-password-123"
        )
        self.owner.role = User.Role.OWNER
        self.owner.save(update_fields=["role"])
        self.player = User.objects.create(
            name="JOGADOR-15",
            email="kallistis-jogador-15@shadow.gravewright.invalid",
            role=User.Role.PARTICIPANT,
            is_active=True,
        )
        self.player.set_unusable_password()
        self.player.save(update_fields=["password"])
        self.access = KallistisPlayerAccess.objects.create(
            user=self.player,
            player_code="JOGADOR-15",
            phrase_lookup_digest=kallistis_phrase_digest(PHRASE),
            phrase_hash=make_password(PHRASE),
        )

    def post_phrase(self, phrase):
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        return self.client.post(
            "/api/auth/player-login",
            data={"phrase": phrase},
            content_type="application/json",
            HTTP_X_CSRF_TOKEN=token,
        )

    def test_phrase_login_starts_participant_session(self):
        response = self.post_phrase("  UNIT-TEST-ACCESS-PHRASE  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account"]["role"], "participant")
        self.assertTrue(self.client.get("/api/auth/session").json()["authenticated"])
        self.assertEqual(self.client.get("/api/home/player").status_code, 200)
        self.assertEqual(self.client.get("/api/home/gm").status_code, 403)

    def test_invalid_and_revoked_phrases_are_uniformly_rejected(self):
        response = self.post_phrase("mi-not-the-phrase")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "invalid_credentials"})
        self.access.revoked_at = timezone.now()
        self.access.save(update_fields=["revoked_at"])
        self.assertEqual(self.post_phrase(PHRASE).status_code, 401)

    def test_phrase_page_does_not_render_email_or_password_fields(self):
        response = self.client.get("/login/player")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="phrase"')
        self.assertNotContains(response, 'name="email"')
        self.assertNotContains(response, 'name="password"')
        self.assertNotContains(response, PHRASE)

    def test_only_digest_and_hash_are_persisted(self):
        access = KallistisPlayerAccess.objects.get(pk=self.access.pk)
        self.assertNotIn(PHRASE, access.phrase_lookup_digest)
        self.assertNotIn(PHRASE, access.phrase_hash)
        self.assertEqual(len(access.phrase_lookup_digest), 64)
