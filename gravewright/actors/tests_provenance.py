"""QA provenance must never grant canonical KALLISTIS authority."""

import os
import tempfile
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings
from django.conf import settings

from gravewright.actors.models import Actor, KallistisCharacterLink
from gravewright.actors.provenance import (
    NON_CANONICAL,
    PROVENANCE_KEY,
    PROVENANCE_SCHEMA,
    SHEET_KEY,
    canonical_link,
    is_canonical,
    qa_fixture_environment_enabled,
    qa_sheet,
    _safe_absolute_path,
    validate_qa_sheet,
)
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


class QaFixtureEnvironmentGuardTests(SimpleTestCase):
    """The official fixture guard accepts only the explicit isolated roots."""

    persistent_root = "/home/tonyus-dev/.local/share/gravewright/playtest-g5"
    product_database = "/home/tonyus-dev/Portifolio/gravewright/data/gravewright.sqlite3"

    def settings_for(self, root=None, database=None, test_database=None, media=None):
        root = root or self.persistent_root
        test_database = test_database or f"{root}/database/test-gravewright.sqlite3"
        return override_settings(
            GRAVEWRIGHT_TACTICAL_QA_FIXTURES_ENABLED=True,
            GRAVEWRIGHT_TACTICAL_QA_FIXTURE_ROOT=root,
            DATABASES={"default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": database or f"{root}/database/gravewright.sqlite3",
                "TEST": {"NAME": test_database},
            }},
            MEDIA_ROOT=media or f"{root}/media",
            DEBUG=True,
            ALLOWED_HOSTS=["127.0.0.1", "localhost", "[::1]"],
            KALLISTIS_VTT_CONSUME_URL="",
            KALLISTIS_VTT_SERVICE_SECRET="",
            KALLISTIS_VTT_CHARACTER_READ_URL="",
            KALLISTIS_ORIGIN="",
            GRAVEWRIGHT_MARKETPLACE_URL="",
            GRAVEWRIGHT_PUBLIC_ORIGIN="",
        )

    def enabled_for(self, **kwargs):
        with self.settings_for(**kwargs), patch.dict(
            os.environ, {"GRAVEWRIGHT_DATABASE": f"{kwargs.get('root', self.persistent_root)}/database/gravewright.sqlite3"}
        ):
            return qa_fixture_environment_enabled()

    def test_explicit_persistent_qa_layout_is_accepted(self):
        self.assertTrue(self.enabled_for())

    def test_legacy_disposable_qa_layout_remains_accepted(self):
        root = "/tmp/gravewright-tactics-qa-20261015/g5.3"
        with self.settings_for(
            root=root,
            database=f"{root}/gravewright.sqlite3",
            test_database=f"{root}/test-gravewright.sqlite3",
            media=f"{root}/media",
        ), patch.dict(os.environ, {"GRAVEWRIGHT_DATABASE": f"{root}/gravewright.sqlite3"}):
            self.assertTrue(qa_fixture_environment_enabled())

    def test_arbitrary_persistent_root_is_rejected(self):
        root = "/home/tonyus-dev/.local/share/gravewright/other-qa"
        self.assertFalse(self.enabled_for(root=root))

    def test_product_sqlite_is_rejected(self):
        self.assertFalse(self.enabled_for(database=self.product_database))

    def test_root_traversal_is_rejected(self):
        root = f"{self.persistent_root}/../playtest-g5"
        self.assertFalse(self.enabled_for(root=root))

    def test_database_outside_authorized_root_is_rejected(self):
        self.assertFalse(self.enabled_for(database="/tmp/not-the-qa-database.sqlite3"))

    def test_media_outside_authorized_root_is_rejected(self):
        self.assertFalse(self.enabled_for(media="/home/tonyus-dev/Portifolio/gravewright/media"))

    def test_symlinked_path_component_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="gravewright-guard-") as temporary:
            link = os.path.join(temporary, "escape")
            os.symlink("/tmp", link)
            self.assertIsNone(_safe_absolute_path(os.path.join(link, "outside.sqlite3")))


class NonCanonicalFixtureBoundaryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "provenance@example.test", "test-password-123", name="Provenance QA", role="owner"
        )
        self.campaign = Campaign.objects.create(name="Provenance QA", owner=self.owner)
        Membership.objects.create(campaign=self.campaign, user=self.owner, role="gm")
        self.actor = Actor.objects.create(
            campaign=self.campaign,
            name="QA only",
            type="character",
            data={"fields": {
                PROVENANCE_KEY: {
                    "schema": PROVENANCE_SCHEMA,
                    "category": "qa_fixture",
                    "authority": NON_CANONICAL,
                },
                SHEET_KEY: {"complete": True},
            }},
        )

    def test_qa_marker_is_never_canonical_and_does_not_query_an_approval_link(self):
        with patch("gravewright.actors.provenance.qa_fixture_environment_enabled", return_value=True):
            with patch("gravewright.actors.provenance.KallistisCharacterLink.objects.filter") as query:
                self.assertIsNone(canonical_link(self.actor))
                query.assert_not_called()
            self.assertEqual(qa_sheet(self.actor), {"complete": True})
            self.assertFalse(is_canonical(self.actor))

    def test_fixture_marker_alone_never_meets_canonical_link_contract(self):
        with patch("gravewright.actors.provenance.qa_fixture_environment_enabled", return_value=True):
            self.assertIsNone(canonical_link(self.actor))
            self.assertFalse(is_canonical(self.actor))

    def test_official_service_creates_seven_valid_noncanonical_records_idempotently(self):
        from gravewright.actors.services import command
        from gravewright.actors.provenance import qa_fixture_environment_enabled

        self.assertTrue(qa_fixture_environment_enabled(), repr({
            "db": settings.DATABASES["default"], "media": settings.MEDIA_ROOT,
            "hosts": settings.ALLOWED_HOSTS, "root": settings.GRAVEWRIGHT_TACTICAL_QA_FIXTURE_ROOT,
            "debug": settings.DEBUG,
        }))

        player = User.objects.create_user(
            "fixture-player@example.test", "test-password-456", name="Fixture Player"
        )
        Membership.objects.create(campaign=self.campaign, user=player, role="player")
        keys = (
            "ally-batedor", "ally-guard", "ally-scout", "silmari-1",
            "silmari-2", "silmari-3", "nomos-evacuee",
        )
        created = [command(
            self.campaign.pk, self.owner.pk, "actor.qa_fixture.create",
            {"fixtureKey": key, "playerId": str(player.pk)}, str(uuid4()),
        ) for key in keys]
        self.assertEqual(len({item["id"] for item in created}), 7)
        for item in created:
            actor = Actor.objects.get(pk=item["id"])
            self.assertTrue(validate_qa_sheet(actor), actor.name)
            self.assertFalse(KallistisCharacterLink.objects.filter(actor=actor).exists())
            self.assertEqual(actor.data["fields"][PROVENANCE_KEY]["authority"], NON_CANONICAL)
        replay = command(
            self.campaign.pk, self.owner.pk, "actor.qa_fixture.create",
            {"fixtureKey": keys[0], "playerId": str(player.pk)}, str(uuid4()),
        )
        self.assertTrue(replay["reused"])
        self.assertEqual(Actor.objects.filter(campaign=self.campaign).count(), 8)

    def test_combat_resource_changes_do_not_invalidate_qa_equipment(self):
        from gravewright.actors.services import command
        from gravewright.combat.kallistis_equipment import equipped_weapon

        player = User.objects.create_user(
            "resource-player@example.test", "test-password-789", name="Resource Player"
        )
        Membership.objects.create(campaign=self.campaign, user=player, role="player")
        result = command(
            self.campaign.pk, self.owner.pk, "actor.qa_fixture.create",
            {"fixtureKey": "ally-batedor", "playerId": str(player.pk)}, str(uuid4()),
        )
        actor = Actor.objects.get(pk=result["id"])
        runtime = actor.data["runtime"]
        runtime["resources"]["vitality"]["current"] -= 1
        runtime["resources"]["breath"]["current"] -= 1
        actor.save(update_fields=["data", "updated_at"])

        self.assertTrue(validate_qa_sheet(actor))
        self.assertEqual(equipped_weapon(actor)["name"], "Faca")
