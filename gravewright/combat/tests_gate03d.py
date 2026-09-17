import uuid

from django.test import TransactionTestCase, override_settings

from gravewright.actors import runtime
from gravewright.actors.models import Actor
from gravewright.maps.models import Broadcast, Scene
from gravewright.maps.services import DEFAULTS, MapError
from gravewright.journals.services import member
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.tokens.models import Token

from . import services


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MinimumCombatTests(TransactionTestCase):
    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.map = Scene.objects.create(
            campaign=self.campaign, name="Combat", width=1400, height=1000, settings=DEFAULTS
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.map)
        self.one = Actor.objects.create(
            campaign=self.campaign, name="One", data=normalize({}),
            permissions={str(self.player.pk): "owner"},
        )
        self.two = Actor.objects.create(
            campaign=self.campaign, name="Two", data=normalize({}),
            permissions={str(self.player.pk): "owner"},
        )
        for actor, x in ((self.one, 0), (self.two, 3)):
            Token.objects.create(scene=self.map, actor=actor, grid_x=x, grid_y=0)
        self.who = member(self.campaign.pk, self.gm.pk)

    def initialize(self, actor, **values):
        return runtime.initialize({"id": actor.pk, **values}, self.who)

    def command(self, command_name, **payload):
        encounter = services.Encounter.objects.filter(scene=self.map).first()
        if encounter:
            payload.setdefault("version", encounter.version)
        return services.command(self.who, command_name, {"sceneId": str(self.map.pk), **payload})

    def start(self):
        self.command("add", tokenId=str(self.one.tokens.first().pk))
        self.command("add", tokenId=str(self.two.tokens.first().pk))
        return self.command("start")

    def test_defenses_structured_resolutions_and_exposed_bonus(self):
        self.initialize(self.one, attributes={"corpo": 2, "agilidade": 3, "vontade": 1, "sintonia": 4}, protection=2)
        self.initialize(self.two, attributes={"corpo": 1, "agilidade": 1, "vontade": 2, "sintonia": 3})
        self.one.refresh_from_db()
        self.assertEqual(services.defenses(self.one), {
            "GUARDA": 15, "FORTITUDE": 13, "INTEGRIDADE": 15, "protection": 2,
        })
        self.start()
        first = self.command(
            "attack", actorId=str(self.one.pk), targetId=str(self.two.tokens.first().pk),
            targetDefense="GUARDA", action={
                "action_label": "Strike", "attribute": {"name": "corpo", "value": 2},
                "skill": {"name": "Combate", "value": 3},
            },
        )["resolution"]["result"]
        self.assertEqual(first["target_defense"], "GUARDA")
        self.assertEqual(first["target_defense_value"], 11)
        runtime.condition({"id": self.two.pk, "conditionType": "EXPOSTO"}, self.who, "runtime.condition.apply")
        second = self.command(
            "resolve", actorId=str(self.one.pk), targetId=str(self.two.tokens.first().pk),
            targetDefense="INTEGRIDADE", action={
                "action_label": "Will", "attribute": {"name": "vontade", "value": 1},
                "skill": {"name": "Influência", "value": 1},
            },
        )["resolution"]["result"]
        self.assertEqual(second["target_defense"], "INTEGRIDADE")
        self.assertEqual(second["condition_modifier"], 2)
        self.assertEqual(second["condition_source"], "Exposto")
        environmental = self.command(
            "resolve", actorId=str(self.one.pk), targetDefense="ENVIRONMENT", difficulty=12,
            action={
                "action_label": "Crossing", "attribute": {"name": "agilidade", "value": 3},
                "skill": {"name": "Atletismo", "value": 1},
            },
        )["resolution"]["result"]
        self.assertEqual(environmental["target_defense"], "DIFFICULTY")
        self.assertEqual(environmental["target_defense_value"], 12)

    def test_damage_pipeline_and_idempotent_down_failure(self):
        self.initialize(self.one, attributes={"corpo": 1, "agilidade": 1, "vontade": 1, "sintonia": 1}, protection=2)
        self.initialize(self.two, attributes={"corpo": 1, "vontade": 1, "sintonia": 1})
        self.start()
        target = str(self.two.tokens.first().pk)
        event_id = str(uuid.uuid4())
        first = self.command("damage", targetId=target, rawDamage=30, protectionValue=2, damageEventId=event_id)["resolution"]["result"]
        self.assertEqual(first["raw_damage"], 30)
        self.assertEqual(first["protection_value"], 2)
        self.assertEqual(first["post_protection_damage"], 28)
        self.assertTrue(first["grave_wound_candidate"])
        second = self.command("damage", targetId=target, rawDamage=20, protectionValue=2, damageEventId=event_id)["resolution"]
        self.assertTrue(second["replayed"])
        actor = Actor.objects.get(pk=self.two.pk)
        self.assertEqual(actor.data["runtime"]["combat"]["permanence_failures"], 0)
        runtime.condition({"id": self.two.pk, "conditionType": "CAIDO"}, self.who, "runtime.condition.apply")
        down_id = str(uuid.uuid4())
        down = self.command("damage", targetId=target, rawDamage=1, damageEventId=down_id)["resolution"]["result"]
        self.assertEqual(down["permanence_failures"], 1)
        replay = self.command("damage", targetId=target, rawDamage=1, damageEventId=down_id)["resolution"]
        self.assertTrue(replay["replayed"])
        self.assertEqual(Actor.objects.get(pk=self.two.pk).data["runtime"]["combat"]["permanence_failures"], 1)

    def test_movement_mode_lento_and_immobilized_are_server_enforced(self):
        self.initialize(self.one, attributes={"corpo": 1})
        self.initialize(self.two, attributes={"corpo": 1})
        state = self.start()
        token = self.one.tokens.first()
        with self.assertRaises(MapError):
            from gravewright.tokens import services as token_services
            token_services.command(self.campaign.pk, self.gm.pk, "move", {
                "mapId": str(self.map.pk), "id": str(token.pk), "gridX": 7, "gridY": 0,
                "expectedVersion": token.version,
            }, uuid.uuid4())
        runtime.condition({"id": self.one.pk, "conditionType": "LENTO"}, self.who, "runtime.condition.apply")
        from gravewright.tokens import services as token_services
        with self.assertRaises(MapError):
            token_services.command(self.campaign.pk, self.player.pk, "move", {
                "mapId": str(self.map.pk), "id": str(token.pk), "gridX": 5, "gridY": 0,
                "expectedVersion": token.version,
            }, uuid.uuid4())
        runtime.condition({"id": self.one.pk, "conditionType": "IMOBILIZADO"}, self.who, "runtime.condition.apply")
        with self.assertRaises(MapError):
            token_services.command(self.campaign.pk, self.gm.pk, "move", {
                "mapId": str(self.map.pk), "id": str(token.pk), "gridX": 1, "gridY": 0,
                "expectedVersion": token.version,
            }, uuid.uuid4())
