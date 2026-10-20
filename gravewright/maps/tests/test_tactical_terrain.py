import uuid

from django.test import TransactionTestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import services
from gravewright.maps.models import Broadcast, Scene, SceneObject, SceneState, TacticalTerrain, TerrainCell
from gravewright.maps.objects import layer_state
from gravewright.maps.services import DEFAULTS, MapError
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.tokens import services as tokens
from gravewright.tokens.models import Token


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TacticalTerrainTests(TransactionTestCase):
    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.scene = Scene.objects.create(
            campaign=self.campaign,
            name="Knossos QA",
            width=1400,
            height=1000,
            settings=DEFAULTS,
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.actor = Actor.objects.create(
            campaign=self.campaign,
            name="Scout QA",
            data=normalize({}),
            permissions={str(self.player.pk): "owner"},
        )

    def scene_command(self, action, data, user=None):
        return services.command(
            self.campaign.pk,
            (user or self.gm).pk,
            "objects",
            {
                "mapId": str(self.scene.pk),
                "area": "terrain",
                "action": action,
                "data": data,
            },
            uuid.uuid4(),
        )

    def initialize(self):
        return self.scene_command("initialize", {"width": 16, "height": 16})

    def test_versioned_grid_projection_and_gm_only_authoring(self):
        response = self.initialize()
        terrain = response["terrain"]
        self.assertEqual((terrain["width"], terrain["height"]), (16, 16))
        self.assertEqual(len(terrain["cells"]), 256)
        self.assertEqual(terrain["schemaVersion"], 1)
        with self.assertRaises(MapError):
            self.scene_command("cell", {"expectedVersion": 1, "x": 0, "y": 0}, self.player)

        edited = self.scene_command("cell", {
            "expectedVersion": 1, "x": 2, "y": 1,
            "terrainType": "DIFICIL", "elevation": 1,
        })["terrain"]
        cell = next(row for row in edited["cells"] if row["x"] == 2 and row["y"] == 1)
        self.assertEqual((cell["terrain_type"], cell["movement_cost"], cell["elevation"]), ("DIFICIL", 2, 1))
        with self.assertRaises(MapError) as conflict:
            self.scene_command("cell", {"expectedVersion": 1, "x": 2, "y": 1, "terrainType": "SEVERO"})
        self.assertEqual(conflict.exception.code, "conflict")

        gm_projection = layer_state(self.scene, services.member(self.campaign.pk, self.gm.pk))["tacticalTerrain"]
        player_projection = layer_state(self.scene, services.member(self.campaign.pk, self.player.pk))["tacticalTerrain"]
        self.assertTrue(gm_projection["canEdit"])
        self.assertFalse(player_projection["canEdit"])
        self.assertEqual(player_projection["cells"], gm_projection["cells"])
        self.assertEqual(SceneState.objects.get(scene=self.scene).version, 3)

    def test_rejected_barriers_and_connected_height_change_are_persistent_and_versioned(self):
        terrain = self.initialize()["terrain"]
        terrain = self.scene_command("cell", {
            "expectedVersion": terrain["version"], "x": 2, "y": 1,
            "terrainType": "INTRANSPONIVEL",
        })["terrain"]
        token = Token.objects.create(scene=self.scene, actor=self.actor, grid_x=1, grid_y=1)
        request_id = uuid.uuid4()
        command = {
            "mapId": str(self.scene.pk), "id": str(token.pk),
            "gridX": 2, "gridY": 1, "expectedVersion": token.version,
        }
        with self.assertRaises(MapError):
            tokens.command(self.campaign.pk, self.player.pk, "move", command, request_id)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.version), (1, 1, 1))

        terrain = self.scene_command("cell", {
            "expectedVersion": terrain["version"], "x": 2, "y": 1,
            "terrainType": "NORMAL", "elevation": 2,
        })["terrain"]
        command.update(gridX=2, gridY=1)
        with self.assertRaises(MapError):
            tokens.command(self.campaign.pk, self.player.pk, "move", command, uuid.uuid4())
        self.scene_command("connect", {
            "expectedVersion": terrain["version"], "x": 1, "y": 1,
            "toX": 2, "toY": 1, "kind": "STAIR",
        })
        tokens.command(self.campaign.pk, self.player.pk, "move", command, uuid.uuid4())
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.elevation, token.version), (2, 1, 2, 2))

    def test_tactical_wall_requires_explicit_audited_gm_override(self):
        self.initialize()
        token = Token.objects.create(scene=self.scene, actor=self.actor, grid_x=1, grid_y=1)
        SceneObject.objects.create(scene=self.scene, kind="walls", data={
            "x1": 140, "y1": 0, "x2": 140, "y2": 220,
            "kind": "wall", "door_state": "closed", "movement_behavior": "block",
            "vertical_bottom": None, "vertical_top": None,
        })
        command = {
            "mapId": str(self.scene.pk), "id": str(token.pk),
            "gridX": 2, "gridY": 1, "expectedVersion": token.version,
        }
        with self.assertRaises(MapError):
            tokens.command(self.campaign.pk, self.gm.pk, "move", command, uuid.uuid4())
        result = tokens.command(
            self.campaign.pk, self.gm.pk, "move", {**command, "gmOverride": True}, uuid.uuid4()
        )
        self.assertEqual(result["movementAudit"]["kind"], "gm_tactical_movement_override")
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (2, 1))

    def test_player_cannot_read_gm_scene_or_author_terrain(self):
        self.initialize()
        player = services.member(self.campaign.pk, self.player.pk)
        private_scene = Scene.objects.create(
            campaign=self.campaign,
            name="GM only QA",
            width=1120,
            height=1120,
            visibility="gm",
            settings=DEFAULTS,
        )
        with self.assertRaises(MapError):
            services.scene(private_scene.pk, player)
        with self.assertRaises(MapError) as denied:
            self.scene_command("cell", {
                "expectedVersion": 1, "x": 6, "y": 1, "terrainType": "SEVERO",
            }, self.player)
        self.assertEqual(denied.exception.code, "forbidden")
