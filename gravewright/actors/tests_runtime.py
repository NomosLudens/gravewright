import uuid
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings

from gravewright.dice import services as dice
from gravewright.dice.kallistis import evaluate
from gravewright.maps.services import MapError
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures

from . import services
from .models import Actor


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
)
class RuntimeTests(TransactionTestCase):
    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.actor = Actor.objects.create(
            campaign=self.campaign, name="Kallistis Hero", data=normalize({}),
            permissions={str(self.player.pk): "owner"},
        )

    def command(self, action, data, user=None, request_id=None):
        return services.command(
            self.campaign.pk, (user or self.gm).pk, action, data,
            request_id or uuid.uuid4(),
        )

    def test_resources_are_bounded_derived_and_idempotent(self):
        request_id = uuid.uuid4()
        result = self.command("runtime.initialize", {
            "id": self.actor.pk,
            "attributes": {"corpo": 2, "vontade": 1, "sintonia": 2, "marco": 3},
        }, request_id=request_id)
        self.assertEqual(result, self.command("runtime.initialize", {
            "id": self.actor.pk,
            "attributes": {"corpo": 2, "vontade": 1, "sintonia": 2, "marco": 3},
        }, request_id=request_id))
        state = result["runtime"]
        self.assertEqual({k: state["resources"][k]["max"] for k in state["resources"]},
                         {"vitality": 16, "lucidity": 11, "flow": 7, "breath": 3, "determination": 3})
        spent = self.command("runtime.resource", {"id": self.actor.pk, "resource": "flow", "operation": "spend", "amount": 2}, user=self.player)
        self.assertEqual(spent["after"], 5)
        with self.assertRaises(MapError):
            self.command("runtime.resource", {"id": self.actor.pk, "resource": "flow", "operation": "spend", "amount": 99}, user=self.player)
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["actors"][0]["runtime"]["resources"]["flow"]["current"], 5)

    def test_conditions_rest_rules_and_zero_transitions(self):
        self.command("runtime.initialize", {"id": self.actor.pk, "attributes": {"sintonia": 2}})
        self.command("runtime.condition.apply", {"id": self.actor.pk, "conditionType": "FRATURADO"})
        self.command("runtime.resource", {"id": self.actor.pk, "resource": "flow", "operation": "spend", "amount": 2})
        safe = self.command("runtime.safe_pause", {"id": self.actor.pk})
        self.assertEqual(safe["runtime"]["resources"]["flow"]["current"], 3)
        self.command("runtime.condition.apply", {"id": self.actor.pk, "conditionType": "FRATURADO"}, request_id=uuid.uuid4())
        self.command("runtime.condition.remove", {"id": self.actor.pk, "conditionType": "FRATURADO"})
        self.command("runtime.resource", {"id": self.actor.pk, "resource": "vitality", "operation": "lose", "amount": 99})
        fallen = self.actor.__class__.objects.get(pk=self.actor.pk)
        self.assertIn("CAIDO", [c["type"] for c in fallen.data["runtime"]["conditions"]])
        self.command("runtime.resource", {"id": self.actor.pk, "resource": "vitality", "operation": "recover", "amount": 1})
        self.assertNotIn("CAIDO", [c["type"] for c in self.actor.__class__.objects.get(pk=self.actor.pk).data["runtime"]["conditions"]])
        self.command("runtime.resource", {"id": self.actor.pk, "resource": "lucidity", "operation": "lose", "amount": 99})
        self.assertTrue(self.actor.__class__.objects.get(pk=self.actor.pk).data["runtime"]["lucidity_zero_pending_resolution"])

    def test_abalado_is_a_single_consumed_action_modifier(self):
        self.command("runtime.initialize", {"id": self.actor.pk})
        self.command("runtime.condition.apply", {"id": self.actor.pk, "conditionType": "ABALADO"})
        action = {"action_label": "Test", "attribute": {"name": "corpo", "value": 2}, "skill": {"name": "Luta", "value": 1}}
        first = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={**action, "actor_id": str(self.actor.pk)}, difficulty=15)
        self.assertEqual(first["roll"]["result"]["condition_modifier"], -2)
        second = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={**action, "actor_id": str(self.actor.pk)}, difficulty=15)
        self.assertNotIn("condition_modifier", second["roll"]["result"])

    def test_determination_reroll_spends_once_and_preserves_audit(self):
        self.command("runtime.initialize", {"id": self.actor.pk})
        original = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={"action_label": "Test", "attribute": {"name": "corpo", "value": 2}, "skill": {"name": "Luta", "value": 1}, "actor_id": str(self.actor.pk)}, difficulty=15)
        original_id = original["id"]
        request_id = uuid.uuid4()
        with patch("gravewright.dice.services.evaluate_kallistis", return_value=evaluate(0, 15, random_source=iter([0.0, 0.0]).__next__)):
            rerolled = dice.reroll(self.campaign.pk, self.player.pk, request_id, original_id)
        rerolled_entry, _ = rerolled
        self.assertEqual(rerolled_entry["roll"]["reroll_of"], original_id)
        self.assertEqual(self.actor.__class__.objects.get(pk=self.actor.pk).data["runtime"]["resources"]["determination"]["current"], 0)
        self.assertEqual(dice.reroll(self.campaign.pk, self.player.pk, request_id, original_id)[0]["id"], rerolled_entry["id"])
        with self.assertRaises(Exception):
            dice.reroll(self.campaign.pk, self.player.pk, uuid.uuid4(), original_id)
