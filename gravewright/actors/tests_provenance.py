"""QA provenance must never grant canonical KALLISTIS authority."""

from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.conf import settings

from gravewright.actors.models import Actor, KallistisCharacterLink
from gravewright.actors.provenance import (
    NON_CANONICAL,
    PROVENANCE_KEY,
    PROVENANCE_SCHEMA,
    SHEET_KEY,
    canonical_link,
    is_canonical,
    qa_sheet,
    validate_qa_sheet,
)
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


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
