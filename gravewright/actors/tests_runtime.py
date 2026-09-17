import uuid
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings

from gravewright.dice import services as dice
from gravewright.dice.kallistis import evaluate
from gravewright.dice.engine import RollError
from gravewright.maps.services import MapError
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures

from . import runtime, services
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

    def test_derived_maxima_change_without_resetting_current_resources(self):
        initial = self.command("runtime.initialize", {
            "id": self.actor.pk,
            "attributes": {"corpo": 2, "vontade": 1, "sintonia": 2, "marco": 3},
            "resources": {"vitality": {"current": 5}, "flow": {"current": 4}},
        })
        self.assertEqual(
            {name: initial["runtime"]["resources"][name]["max"] for name in ("vitality", "lucidity", "flow")},
            {"vitality": 16, "lucidity": 11, "flow": 7},
        )
        changed = self.command("runtime.initialize", {
            "id": self.actor.pk,
            "attributes": {"corpo": 1, "vontade": 2, "sintonia": 1, "marco": 1},
        })
        self.assertEqual(changed["runtime"]["resources"]["vitality"], {"current": 5, "max": 13})
        self.assertEqual(changed["runtime"]["resources"]["lucidity"], {"current": 11, "max": 14})
        self.assertEqual(changed["runtime"]["resources"]["flow"], {"current": 4, "max": 5})

    def test_resource_commands_clamp_at_documented_minimum_and_maximum(self):
        self.command("runtime.initialize", {
            "id": self.actor.pk, "attributes": {"corpo": 1},
            "resources": {"vitality": {"current": 1}},
        })
        lost = self.command("runtime.resource", {
            "id": self.actor.pk, "resource": "vitality", "operation": "lose", "amount": 99,
        }, user=self.player)
        self.assertEqual(lost["after"], 0)
        gained = self.command("runtime.resource", {
            "id": self.actor.pk, "resource": "vitality", "operation": "gain", "amount": 99,
        }, user=self.player)
        self.assertEqual(gained["after"], gained["runtime"]["resources"]["vitality"]["max"])
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["actors"][0]["runtime"]["resources"]["vitality"]["current"], 13)

    def test_kallistis_actor_runtime_persists_canonical_attributes_and_skills(self):
        attributes = {
            "corpo": 3, "agilidade": 2, "intelecto": 2,
            "presenca": 1, "vontade": 1, "sintonia": 0,
        }
        skills = {name: index % 6 for index, name in enumerate(runtime.SKILL_NAMES)}
        result = self.command("runtime.initialize", {
            "id": self.actor.pk, "attributes": attributes, "skills": skills,
        }, user=self.player)
        self.assertEqual(set(result["runtime"]["attributes"]) - {"marco"}, set(runtime.ATTRIBUTE_NAMES))
        self.assertEqual(set(result["runtime"]["skills"]), set(runtime.SKILL_NAMES))
        self.assertEqual(result["runtime"]["attributes"], {**attributes, "marco": 0})
        self.assertEqual(result["runtime"]["skills"], skills)
        self.actor.refresh_from_db()
        persisted = services.state(self.campaign.pk, self.player.pk)["actors"][0]["runtime"]
        self.assertEqual(persisted["attributes"], result["runtime"]["attributes"])
        self.assertEqual(persisted["skills"], skills)

    def test_linked_kallistis_roll_uses_actor_values_and_rejects_invalid_authority(self):
        self.command("runtime.initialize", {
            "id": self.actor.pk,
            "attributes": {"corpo": 4}, "skills": {"combate": 5},
        }, user=self.player)
        action = {
            "action_label": "Anti-tampering",
            "attribute": {"name": "Corpo", "value": 999},
            "skill": {"name": "Combate", "value": 999},
            "actor_id": str(self.actor.pk),
        }
        entry = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                          system="kallistis", mode="action", action=action, difficulty=15)
        persisted_action = entry["roll"]["action"]
        self.assertEqual(persisted_action["attribute"]["value"], 4)
        self.assertEqual(persisted_action["skill"]["value"], 5)
        self.assertEqual(persisted_action["base_modifier"], 9)
        self.assertEqual(entry["roll"]["modifier"], 9)

        invalid = {**action, "attribute": {"name": "不存在", "value": 0}}
        with self.assertRaises((MapError, RollError)):
            dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                      system="kallistis", mode="action", action=invalid)
        invalid = {**action, "skill": {"name": "Coerção", "value": 0}}
        with self.assertRaises(MapError):
            dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                      system="kallistis", mode="action", action=invalid)
        invalid = {**action, "actor_id": str(uuid.uuid4())}
        with self.assertRaises(MapError):
            dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                      system="kallistis", mode="action", action=invalid)

    def test_linked_actor_roll_rejects_foreign_and_read_only_actor(self):
        foreign = Actor.objects.create(campaign=self.other, name="Foreign", data=normalize({}))
        action = {
            "action_label": "Boundary",
            "attribute": {"name": "Corpo", "value": 0},
            "skill": {"name": "Atletismo", "value": 0},
            "actor_id": str(foreign.pk),
        }
        with self.assertRaises(MapError):
            dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                      system="kallistis", mode="action", action=action)
        self.actor.permissions = {str(self.player.pk): "read"}
        self.actor.save(update_fields=["permissions"])
        action["actor_id"] = str(self.actor.pk)
        with self.assertRaises(MapError):
            dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(),
                      system="kallistis", mode="action", action=action)

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
        action = {"action_label": "Test", "attribute": {"name": "corpo", "value": 2}, "skill": {"name": "Combate", "value": 1}}
        first = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={**action, "actor_id": str(self.actor.pk)}, difficulty=15)
        self.assertEqual(first["roll"]["result"]["condition_modifier"], -2)
        second = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={**action, "actor_id": str(self.actor.pk)}, difficulty=15)
        self.assertNotIn("condition_modifier", second["roll"]["result"])

    def test_determination_reroll_spends_once_and_preserves_audit(self):
        self.command("runtime.initialize", {"id": self.actor.pk})
        original = dice.roll(self.campaign.pk, self.player.pk, "2d10", uuid.uuid4(), system="kallistis", mode="action", action={"action_label": "Test", "attribute": {"name": "corpo", "value": 2}, "skill": {"name": "Combate", "value": 1}, "actor_id": str(self.actor.pk)}, difficulty=15)
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
