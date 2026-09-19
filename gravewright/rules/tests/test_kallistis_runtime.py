from django.test import SimpleTestCase

from gravewright.rules import kallistis_runtime as rules


class ResolutionTests(SimpleTestCase):
    def test_every_boundary_grade_is_canonical(self):
        cases = [(-5, "failure_severe"), (-1, "failure"), (0, "success"), (4, "success"), (5, "success_strong"), (9, "success_strong"), (10, "success_extraordinary")]
        for margin, expected in cases:
            result = rules.resolve_test(light=5, dark=5, attribute=margin, skill=0, difficulty=10)
            self.assertEqual(result["grade"], expected)
            self.assertEqual(result["margin"], margin)

    def test_light_and_dark_remain_separate_and_resonance_is_not_critical(self):
        result = rules.resolve_test(light=2, dark=2, difficulty=4)
        self.assertEqual(result["predominance"], "resonance")
        self.assertTrue(result["resonance"])
        self.assertFalse(result["critical"])
        self.assertEqual(result["light_face"]["value"], 2)
        self.assertEqual(result["dark_face"]["value"], 2)

    def test_predominance_does_not_change_success(self):
        light = rules.resolve_test(light=10, dark=1, difficulty=30)
        dark = rules.resolve_test(light=1, dark=10, difficulty=30)
        self.assertFalse(light["success"])
        self.assertFalse(dark["success"])
        self.assertEqual(light["predominance"], "light")
        self.assertEqual(dark["predominance"], "dark")

    def test_impulse_pressure_and_help_have_caps_and_distinct_sources(self):
        result = rules.resolve_test(
            light=5, dark=5, difficulty=20,
            impulse_sources=[{"id": "tool", "steps": 2}, {"id": "position", "steps": 2}],
            pressure_sources=[{"id": "wound", "steps": 3}],
            helpers=["ally-1", "ally-2"],
        )
        self.assertEqual(result["impulse_bonus"], 4)
        self.assertEqual(result["pressure_penalty"], -4)
        self.assertEqual(result["helper_count"], 2)
        with self.assertRaises(rules.RuleError):
            rules.resolve_test(light=5, dark=5, impulse_sources=["same", "same"])

    def test_opposed_tie_defaults_to_established_defender(self):
        result = rules.opposed_test({"attribute": 1, "skill": 0}, {"attribute": 1, "skill": 0}, random_source=iter([0.4, 0.4, 0.4, 0.4]).__next__)
        self.assertEqual(result["winner"], "defender")
        self.assertTrue(result["tie"])


class RuntimeStateTests(SimpleTestCase):
    def setUp(self):
        self.state = rules.new_session_state({"corpo": 2, "vontade": 1, "sintonia": 2, "marco": 5}, {"atletismo": 2, "magia": 2, "evocacao": 2})

    def test_derived_resources_match_book(self):
        self.assertEqual(self.state["resources"]["vitality"], {"current": 16, "max": 16})
        self.assertEqual(self.state["resources"]["lucidity"], {"current": 11, "max": 11})
        self.assertEqual(self.state["resources"]["flow"], {"current": 8, "max": 8})
        self.assertEqual(self.state["action_economy"]["movement"], 6)

    def test_safe_pause_and_full_rest_obey_fractured_and_determination_rules(self):
        self.state["resources"]["flow"]["current"] = 0
        self.state["resources"]["vitality"]["current"] = 1
        self.state["resources"]["determination"]["current"] = 2
        rules.add_condition(self.state, "FRATURADO")
        safe = rules.safe_pause(self.state)
        self.assertTrue(safe["flow_blocked"])
        full = rules.full_rest(self.state)
        self.assertEqual(full["state"]["resources"]["determination"]["current"], 2)
        self.assertEqual(full["state"]["resources"]["vitality"]["current"], 16)

    def test_action_economy_and_movement_are_server_bounded(self):
        rules.begin_round(self.state)
        rules.spend_action(self.state, "action")
        with self.assertRaises(rules.RuleError):
            rules.spend_action(self.state, "action")
        result = rules.run_movement(self.state, [(0, 0), (1, 0), (2, 1)], terrain="NORMAL")
        self.assertEqual(result["cost"], 3)
        with self.assertRaises(rules.RuleError):
            rules.run_movement(self.state, [(0, 0), (7, 0)], terrain="NORMAL")

    def test_damage_and_permanence(self):
        result = rules.apply_damage(self.state, 99, protection=2, fortitude=13)
        self.assertEqual(result["after"], 0)
        self.assertTrue(result["grave_wound_candidate"])
        first = rules.permanence(self.state, light=1, dark=1)
        self.assertEqual(first["state"]["combat"]["permanence_failures"], 1)

    def test_lucidity_zero_requires_explicit_player_choice(self):
        self.state["resources"]["lucidity"]["current"] = 0
        with self.assertRaises(rules.RuleError):
            rules.lucidity_zero(self.state, "mind_control")
        result = rules.lucidity_zero(self.state, "return_one")
        self.assertEqual(result["state"]["resources"]["lucidity"]["current"], 1)


class SubsystemsTests(SimpleTestCase):
    def setUp(self):
        self.state = rules.new_session_state({"sintonia": 4, "vontade": 2, "marco": 15}, {"magia": 3, "evocacao": 3, "empatia": 3})

    def test_technique_magic_epic_and_g7_boundary(self):
        self.assertTrue(rules.technique(marco=6, minimum_marco=6)["legal"])
        self.assertEqual(rules.magic(grade=6, marco=15)["multiplier"], 4)
        with self.assertRaises(rules.RuleError):
            rules.magic(grade=7, marco=15)

    def test_evocation_and_merge_preserve_cost_and_consent(self):
        evocation = rules.evocation(kind="major", tuning=4, evocation_skill=3, flow_available=8)
        self.assertEqual(evocation["profile"]["cost"], 3)
        merge = rules.merge(mode="voluntary_union", consent=True, tuning=4, skill=3, flow_available=8, benefits=["shared_sense"])
        self.assertTrue(merge["active"])
        with self.assertRaises(rules.RuleError):
            rules.merge(mode="voluntary_union", consent=False, tuning=4, skill=3, flow_available=8)

    def test_coro_is_shared_and_requires_full_bar_to_spend(self):
        self.state["coro"] = rules.coro_state(4)
        for _ in range(4): rules.add_coro_pulse(self.state)
        self.assertEqual(self.state["coro"]["pulses"], 4)
        spent = rules.spend_coro(self.state, "amparo", 2)
        self.assertEqual(spent["state"]["coro"]["pulses"], 0)

    def test_shadow_fissure_fulgor_and_progression_limits(self):
        shadow = rules.change_shadow(self.state, 6, reason="forced_merge")
        self.assertEqual(shadow["state_name"], "crise_identidade")
        fissure = rules.fissure_traversal(state_name="ABERTA", contributions=[{"success": True}, {"success": True}, {"success": True}])
        self.assertTrue(fissure["stable"])
        fulgor = rules.fulgor_gain(self.state, 5)
        self.assertTrue(fulgor["fulgor_pleno"])
        self.assertFalse(rules.progression_contract(16)["playable"])

    def test_equipment_and_artifact_frequency(self):
        self.assertEqual(rules.WEAPONS["espada"]["damage"], 5)
        self.assertEqual(rules.equipment_load(2, [{"spaces": 3}, {"light": True}])["used"], 4)
        rules.artifact_use(self.state, "ampulheta", frequency="session")
        with self.assertRaises(rules.RuleError):
            rules.artifact_use(self.state, "ampulheta", frequency="session")
