import uuid
from unittest.mock import patch

from django.test import TestCase

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Broadcast, Scene, SceneObject, TacticalTerrain, TerrainCell, TerrainConnection
from gravewright.maps.services import MapError
from gravewright.pdf_system.schema import normalize
from gravewright.table import domain
from gravewright.tokens.models import Token
from gravewright.tokens import services as token_services

from .models import Encounter, MissionDefinition, MissionInstance, MissionParticipant
from gravewright.actors.models import KallistisCharacterLink


class TacticalMissionTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user(email="mission-gm@example.test", password="long-test-password", name="GM", role="owner")
        self.player = User.objects.create_user(email="mission-player@example.test", password="long-test-password", name="Player")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Mission QA")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        self.scene = Scene.objects.create(campaign=self.campaign, name="Knossos QA", width=1120, height=1120)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.terrain = TacticalTerrain.objects.create(scene=self.scene, width=16, height=16)
        cells = [TerrainCell(terrain=self.terrain, x=x, y=y) for y in range(16) for x in range(16)]
        cells[17].elevation = 1
        cells[18].traversable = False
        TerrainCell.objects.bulk_create(cells)
        by_xy = {(cell.x, cell.y): cell for cell in TerrainCell.objects.filter(terrain=self.terrain)}
        TerrainConnection.objects.create(terrain=self.terrain, cell_a=by_xy[(0, 1)], cell_b=by_xy[(1, 1)], kind="STAIR")
        SceneObject.objects.create(scene=self.scene, kind="walls", data={
            "kind": "wall", "x1": 70, "y1": 70, "x2": 140, "y2": 70,
            "door_state": "closed", "movement_behavior": "block",
        })
        self.definition = MissionDefinition.objects.get(key="knossos-evacuation", version=1)

    def command(self, action, data, user=None, request_id=None):
        payload = {"sceneId": str(self.scene.pk), **data}
        if action.startswith("mission.") and action != "mission.create":
            payload["combatVersion"] = domain.state(self.campaign.pk, (user or self.gm).pk, "combat", str(self.scene.pk))["version"]
        if action != "mission.create" and "version" not in payload:
            mission = MissionInstance.objects.filter(scene=self.scene).first()
            payload["version"] = mission.version if mission else 1
        return domain.command(
            self.campaign.pk, (user or self.gm).pk, "combat", action, payload,
            request_id or uuid.uuid4(),
        )

    def combat_command(self, action, data):
        current = domain.state(self.campaign.pk, self.gm.pk, "combat", str(self.scene.pk))
        return domain.command(
            self.campaign.pk, self.gm.pk, "combat", action,
            {"sceneId": str(self.scene.pk), "version": current["version"], **data}, uuid.uuid4(),
        )

    def _add_roster(self):
        participants = []
        for index in range(7):
            role = MissionParticipant.ALLY if index < 3 else MissionParticipant.HOSTILE if index < 6 else MissionParticipant.EVACUEE
            people = {"id": "nomos", "heritage": "reparador"} if role == MissionParticipant.EVACUEE else (
                {"id": "kragor", "heritage": "escudo_do_cla"} if role == MissionParticipant.ALLY
                else {"id": "aelvari", "heritage": "cronista"}
            )
            runtime = {"people": people}
            data = normalize({})
            data["runtime"] = runtime
            track = [{"oficio": "Batedor", "marco": 2, "tecnicas": ["Emboscada"]}] if index == 0 else []
            data["fields"] = {"kallistis_source_snapshot": {
                "completo": True,
                "trilhaAtiva": 0,
                "trilhas": track,
                "equipamento": {"arma": "Machado" if index == 0 else "Faca", "proficienciaConfirmada": True},
            }}
            permissions = {str(self.player.pk): "owner"} if index == 0 else {}
            actor = Actor.objects.create(campaign=self.campaign, name=f"QA {index}", data=data, permissions=permissions)
            KallistisCharacterLink.objects.create(
                actor=actor, kallistis_character_id=f"qa-character-{index}",
                source_state="approved", canonical=True,
            )
            token = Token.objects.create(scene=self.scene, actor=actor)
            result = self.command("mission.participant.add", {"actorId": str(actor.pk), "tokenId": str(token.pk), "role": role})
            participants.append((role, actor, token, result))
        return participants

    def test_definition_is_noncanonical_and_source_technique_is_explicit(self):
        content = self.definition.content
        self.assertEqual(content["canonStatus"], "NON_CANONICAL_MISSION_PROPOSAL")
        self.assertEqual(content["technique"]["name"], "Emboscada")
        self.assertEqual(content["technique"]["cost"], {"resource": "breath", "amount": 1})
        self.assertEqual(content["technique"]["eligibility"]["activeProfession"], "Batedor")
        self.assertIn("SERVER_ATTACK_VALIDATION", content["technique"]["implementationStatus"])

    def test_mission_roster_ready_and_evacuating_nomos(self):
        self.command("mission.create", {"definition": self.definition.key})
        roster = self._add_roster()
        state = self.command("mission.ready", {})
        self.assertEqual(state["mission"]["state"], MissionInstance.READY)
        self.combat_command("roll-initiative", {
            "friendlyRepresentative": str(roster[0][2].pk),
            "hostileRepresentative": str(roster[3][2].pk),
        })
        self.combat_command("choose-first-side", {"side": "friendly"})
        self.combat_command("start", {})
        mission = MissionInstance.objects.get(scene=self.scene)
        state = self.command("mission.start", {"version": mission.version})
        self.assertEqual(state["mission"]["state"], MissionInstance.ACTIVE)
        evacuee = roster[-1][2]
        path = [{"gridX": x, "gridY": 0} for x in range(1, 15)]
        path.extend({"gridX": 14, "gridY": y} for y in range(1, 15))
        token_services.command(
            self.campaign.pk,
            self.gm.pk,
            "move",
            {"mapId": str(self.scene.pk), "id": str(evacuee.pk), "gridX": 14, "gridY": 14,
             "path": path, "expectedVersion": evacuee.version, "gmOverride": True},
            uuid.uuid4(),
        )
        mission = MissionInstance.objects.get(scene=self.scene)
        self.assertEqual(mission.state, MissionInstance.VICTORY)
        evacuee.refresh_from_db()
        self.assertEqual((evacuee.grid_x, evacuee.grid_y), (14, 14))
        self.assertEqual(mission.result["reason"], "nomos_extracted")
        self.assertEqual(list(mission.events.values_list("kind", flat=True))[-1], "objective.resolved")
        with self.assertRaises(MapError):
            self.combat_command("next", {})
        self.assertFalse(Encounter.objects.get(scene=self.scene).active)

    def test_player_cannot_create_or_transition_mission(self):
        with self.assertRaises(MapError):
            self.command("mission.create", {}, self.player)
        self.command("mission.create", {})
        with self.assertRaises(MapError):
            self.command("mission.abort", {}, self.player)

    def test_mission_create_request_replay_does_not_duplicate_instance_or_event(self):
        request_id = uuid.uuid4()
        payload = {"sceneId": str(self.scene.pk), "definition": self.definition.key}
        first = domain.command(self.campaign.pk, self.gm.pk, "combat", "mission.create", payload, request_id)
        replay = domain.command(self.campaign.pk, self.gm.pk, "combat", "mission.create", payload, request_id)
        self.assertEqual(first, replay)
        self.assertEqual(MissionInstance.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(MissionInstance.objects.get(scene=self.scene).events.count(), 1)

    def test_tactical_melee_checks_turn_target_adjacency_and_line_of_effect(self):
        self.command("mission.create", {"definition": self.definition.key})
        roster = self._add_roster()
        attacker = roster[0][1]
        target = roster[3][1]
        attacker_token = roster[0][2]
        target_token = roster[3][2]
        Token.objects.filter(pk=attacker_token.pk).update(grid_x=1, grid_y=1)
        Token.objects.filter(pk=target_token.pk).update(grid_x=4, grid_y=1)
        self.command("mission.ready", {})
        self.combat_command("roll-initiative", {
            "friendlyRepresentative": str(attacker_token.pk),
            "hostileRepresentative": str(target_token.pk),
        })
        self.combat_command("choose-first-side", {"side": "friendly"})
        self.combat_command("start", {})
        mission = MissionInstance.objects.get(scene=self.scene)
        self.command("mission.start", {"version": mission.version})
        payload = {
            "sceneId": str(self.scene.pk),
            "version": domain.state(self.campaign.pk, self.player.pk, "combat", str(self.scene.pk))["version"],
            "actorId": str(attacker.pk),
            "targetId": str(target_token.pk),
            "targetDefense": "GUARDA",
            "action": {"action_label": "Golpe adjacente", "attribute": {"name": "Corpo"}, "skill": {"name": "Combate"}},
        }
        with self.assertRaises(MapError) as out_of_range:
            domain.command(self.campaign.pk, self.player.pk, "combat", "attack", payload, uuid.uuid4())
        self.assertEqual(out_of_range.exception.code, "out_of_range", str(out_of_range.exception))
        Token.objects.filter(pk=target_token.pk).update(grid_x=2)
        wall = SceneObject.objects.get(scene=self.scene, kind="walls")
        wall.data = {**wall.data, "x1": 140, "y1": 0, "x2": 140, "y2": 220}
        wall.save(update_fields=["data"])
        with self.assertRaises(MapError) as blocked_attack:
            domain.command(self.campaign.pk, self.player.pk, "combat", "attack", payload, uuid.uuid4())
        self.assertEqual(blocked_attack.exception.code, "blocked_line_of_effect")
        wall.delete()
        result = domain.command(self.campaign.pk, self.player.pk, "combat", "attack", payload, uuid.uuid4())
        self.assertEqual(result["resolution"]["result"]["target_defense"], "GUARDA")

    def test_emboscada_uses_canonical_active_track_and_applies_server_effects(self):
        self.command("mission.create", {"definition": self.definition.key})
        roster = self._add_roster()
        attacker, target = roster[0][1], roster[3][1]
        attacker_token, target_token = roster[0][2], roster[3][2]
        Token.objects.filter(pk=attacker_token.pk).update(grid_x=1, grid_y=1)
        Token.objects.filter(pk=target_token.pk).update(grid_x=2, grid_y=1)
        attacker_data = attacker.data
        attacker_data["fields"]["kallistis_source_snapshot"].update({
            "trilhaAtiva": 0,
            "trilhas": [{"oficio": "Batedor", "marco": 2, "tecnicas": ["Emboscada"]}],
        })
        attacker.data = attacker_data
        attacker.save(update_fields=["data"])
        self.command("mission.ready", {})
        self.combat_command("roll-initiative", {
            "friendlyRepresentative": str(attacker_token.pk),
            "hostileRepresentative": str(target_token.pk),
        })
        self.combat_command("choose-first-side", {"side": "friendly"})
        self.combat_command("start", {})
        mission = MissionInstance.objects.get(scene=self.scene)
        self.command("mission.start", {"version": mission.version})
        payload = {
            "sceneId": str(self.scene.pk),
            "version": Encounter.objects.get(scene=self.scene).version,
            "actorId": str(attacker.pk),
            "targetId": str(target_token.pk),
            "targetDefense": "GUARDA",
            "technique": "Emboscada",
            "action": {"action_label": "Emboscada", "attribute": {"name": "Corpo"}, "skill": {"name": "Combate"}},
        }
        request_id = uuid.uuid4()
        result = domain.command(self.campaign.pk, self.player.pk, "combat", "attack", payload, request_id)
        replay = domain.command(self.campaign.pk, self.player.pk, "combat", "attack", payload, request_id)
        self.assertEqual(result, replay)
        technique = result["resolution"]["result"]["technique"]
        self.assertEqual(technique["damageBaseMultiplier"], 2)
        self.assertEqual(result["resolution"]["result"]["damageProfile"]["power"], 1)
        attacker.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(attacker.data["runtime"]["resources"]["breath"]["current"], 2)
        self.assertIn("EXPOSTO", {condition["type"] for condition in target.data["runtime"]["conditions"]})

    def test_active_tactical_damage_uses_saved_attack_and_canonical_weapon_formula(self):
        self.command("mission.create", {"definition": self.definition.key})
        roster = self._add_roster()
        attacker, target = roster[0][1], roster[3][1]
        attacker_token, target_token = roster[0][2], roster[3][2]
        Token.objects.filter(pk=attacker_token.pk).update(grid_x=1, grid_y=1)
        Token.objects.filter(pk=target_token.pk).update(grid_x=2, grid_y=1)
        attacker_data = attacker.data
        attacker_data["runtime"]["attributes"] = {"corpo": 3}
        attacker.data = attacker_data
        attacker.save(update_fields=["data"])
        target_data = target.data
        target_data["runtime"]["attributes"] = {"corpo": 20}
        target_data["runtime"]["resources"] = {"vitality": {"current": 70}}
        target_data["runtime"]["protection"] = 2
        target.data = target_data
        target.save(update_fields=["data"])
        self.command("mission.ready", {})
        self.combat_command("roll-initiative", {
            "friendlyRepresentative": str(attacker_token.pk),
            "hostileRepresentative": str(target_token.pk),
        })
        self.combat_command("choose-first-side", {"side": "friendly"})
        self.combat_command("start", {})
        mission = MissionInstance.objects.get(scene=self.scene)
        self.command("mission.start", {"version": mission.version})
        attack_payload = {
            "sceneId": str(self.scene.pk),
            "version": Encounter.objects.get(scene=self.scene).version,
            "actorId": str(attacker.pk),
            "targetId": str(target_token.pk),
            "targetDefense": "GUARDA",
            "action": {"action_label": "Ataque QA", "attribute": {"name": "Corpo"}, "skill": {"name": "Combate"}},
        }
        certain_success = {
            "success": True, "degree": "success_strong", "total": 20,
            "light_die": 10, "dark_die": 10,
        }
        with patch("gravewright.combat.services.evaluate_kallistis", return_value=certain_success):
            attack = self.combat_command("attack", attack_payload)["resolution"]["result"]
        self.assertEqual(attack["damageProfile"]["weaponName"], "Machado")
        self.assertEqual(attack["damageProfile"]["power"], 0)
        self.assertEqual(attack["damageProfile"]["bodyBonus"], 3)
        damage_payload = {
            "sceneId": str(self.scene.pk),
            "version": Encounter.objects.get(scene=self.scene).version,
            "targetId": str(target_token.pk),
            "attackResolutionId": attack["resolutionId"],
            "damageEventId": str(uuid.uuid4()),
        }
        damage = self.combat_command("damage", damage_payload)["resolution"]["result"]
        self.assertEqual(damage["damage_calculation"]["raw"], 11)
        self.assertEqual(damage["damage_calculation"]["final"], 9)
        self.assertEqual(damage["post_protection_damage"], 9)
        target.refresh_from_db()
        self.assertEqual(target.data["runtime"]["resources"]["vitality"]["current"], 61)
        current_version = Encounter.objects.get(scene=self.scene).version
        with self.assertRaises(MapError) as forged:
            self.combat_command("damage", {**damage_payload, "version": current_version, "damageEventId": str(uuid.uuid4()), "rawDamage": 1000})
        self.assertEqual(forged.exception.code, "invalid_damage_payload")
        with self.assertRaises(MapError) as duplicate:
            self.combat_command("damage", {**damage_payload, "version": current_version, "damageEventId": str(uuid.uuid4())})
        self.assertEqual(duplicate.exception.code, "damage_already_applied")
