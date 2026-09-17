from unittest import TestCase

from gravewright.dice.engine import RollError
from gravewright.dice.kallistis import (
    ATTRIBUTES,
    DARK_PRINCIPLES,
    DIFFICULTY_PRESETS,
    LIGHT_PRINCIPLES,
    RESONANCES,
    evaluate,
    prepare_action,
)


def source(*values):
    return iter(values).__next__


class KallistisEngineTests(TestCase):
    def test_light_and_dark_faces_preserve_values_and_invert_glyphs(self):
        expected = {
            "light": {1: "dark", 10: "light"},
            "dark": {1: "light", 10: "dark"},
        }
        for die in ("light", "dark"):
            for value in range(1, 11):
                samples = ((value - 1) / 10, 0) if die == "light" else (0, (value - 1) / 10)
                with self.subTest(die=die, value=value):
                    result = evaluate(0, 100, random_source=source(*samples))
                    face = result[f"{die}_face"]
                    self.assertEqual(result[f"{die}_die"], value)
                    self.assertEqual(face["value"], value)
                    if value in expected[die]:
                        self.assertEqual(face["kind"], "glyph")
                        self.assertEqual(face["glyph"], expected[die][value])
                    else:
                        self.assertEqual(face, {"value": value, "kind": "number", "glyph": None})

    def test_crossed_glyphs_keep_die_identity_and_numeric_values(self):
        for light, dark, light_glyph, dark_glyph in [
            (10, 10, "light", "dark"),
            (1, 1, "dark", "light"),
            (10, 1, "light", "light"),
            (1, 10, "dark", "dark"),
        ]:
            with self.subTest(light=light, dark=dark):
                result = evaluate(0, 100, random_source=source((light - 1) / 10, (dark - 1) / 10))
                self.assertEqual((result["light_die"], result["dark_die"]), (light, dark))
                self.assertEqual(result["light_face"]["glyph"], light_glyph)
                self.assertEqual(result["dark_face"]["glyph"], dark_glyph)
                self.assertEqual(result["natural_total"], light + dark)

    def test_light_predominance_success_and_positive_margin(self):
        result = evaluate(1, 10, random_source=source(0.7, 0.4))
        self.assertEqual(result["light_die"], 8)
        self.assertEqual(result["dark_die"], 5)
        self.assertEqual(result["natural_total"], 13)
        self.assertEqual(result["modifier"], 1)
        self.assertEqual(result["total"], 14)
        self.assertEqual(result["difficulty"], 10)
        self.assertEqual(result["margin"], 4)
        self.assertTrue(result["success"])
        self.assertEqual(result["degree"], "success")
        self.assertEqual(result["predominance"], "light")
        self.assertEqual(result["light_principle"], "testemunho")
        self.assertEqual(result["dark_principle"], "vinculo")
        self.assertEqual(result["predominance_delta"], 3)
        self.assertEqual(result["predominance_intensity"], "clear")
        self.assertEqual(result["grade"], result["degree"])
        self.assertFalse(result["resonance"])

    def test_dark_predominance_and_failure_with_negative_margin(self):
        result = evaluate(0, 15, random_source=source(0.1, 0.8))
        self.assertEqual((result["light_die"], result["dark_die"]), (2, 9))
        self.assertEqual(result["margin"], -4)
        self.assertFalse(result["success"])
        self.assertEqual(result["predominance"], "dark")
        self.assertEqual(result["light_principle"], "vestigio")
        self.assertEqual(result["dark_principle"], "profundidade")
        self.assertEqual(result["predominance_delta"], 7)
        self.assertEqual(result["predominance_intensity"], "intense")

    def test_resonance_1_1(self):
        result = evaluate(0, 2, random_source=source(0, 0))
        self.assertEqual((result["light_die"], result["dark_die"]), (1, 1))
        self.assertTrue(result["success"])
        self.assertEqual(result["margin"], 0)
        self.assertEqual(result["predominance"], "resonance")
        self.assertTrue(result["resonance"])
        self.assertEqual(result["resonance_value"], 1)
        self.assertEqual(result["resonance_name"], "Ressonância Frágil")
        self.assertEqual(result["resonance_opening"], "algo pequeno sobrevive, começa ou recusa desaparecer")
        self.assertEqual(result["predominance_intensity"], "resonance")

    def test_resonance_10_10(self):
        result = evaluate(0, 21, random_source=source(0.999999, 0.999999))
        self.assertEqual((result["light_die"], result["dark_die"]), (10, 10))
        self.assertFalse(result["success"])
        self.assertEqual(result["margin"], -1)
        self.assertTrue(result["resonance"])
        self.assertEqual(result["resonance_value"], 10)
        self.assertEqual(result["resonance_name"], "Ressonância Plena")

    def test_strong_and_extraordinary_degrees(self):
        strong = evaluate(0, 15, random_source=source(0.9, 0.9))
        extraordinary = evaluate(0, 9, random_source=source(0.9, 0.8))
        self.assertEqual(strong["degree"], "success_strong")
        self.assertEqual(extraordinary["degree"], "success_extraordinary")

    def test_modifier_is_applied_once_and_repeated_rolls_are_independent(self):
        results = evaluate(2, 10, repeat=2, random_source=source(0, 0.1, 0.2, 0.3))
        self.assertEqual([(r["light_die"], r["dark_die"]) for r in results], [(1, 2), (3, 4)])
        self.assertEqual([r["total"] for r in results], [5, 9])
        self.assertEqual([r["modifier"] for r in results], [2, 2])

    def test_all_light_and_dark_faces_have_canonical_readings(self):
        self.assertEqual(set(LIGHT_PRINCIPLES), set(range(1, 11)))
        self.assertEqual(set(DARK_PRINCIPLES), set(range(1, 11)))
        for face in range(1, 11):
            with self.subTest(light=face):
                result = evaluate(0, 100, random_source=source((face - 1) / 10, 0))
                self.assertEqual(result["light_principle"], LIGHT_PRINCIPLES[face]["key"])
                self.assertEqual(result["light_principle_label"], LIGHT_PRINCIPLES[face]["label"])
                self.assertEqual(result["light_reading"]["success"], LIGHT_PRINCIPLES[face]["success"])
            with self.subTest(dark=face):
                result = evaluate(0, 100, random_source=source(0, (face - 1) / 10))
                self.assertEqual(result["dark_principle"], DARK_PRINCIPLES[face]["key"])
                self.assertEqual(result["dark_principle_label"], DARK_PRINCIPLES[face]["label"])
                self.assertEqual(result["dark_reading"]["failure"], DARK_PRINCIPLES[face]["failure"])

    def test_predominance_delta_and_intensity(self):
        cases = [
            (10, 1, "light", 9, "absolute"),
            (1, 10, "dark", 9, "absolute"),
            (8, 5, "light", 3, "clear"),
            (6, 5, "light", 1, "subtle"),
        ]
        for light, dark, predominance, delta, intensity in cases:
            with self.subTest(light=light, dark=dark):
                result = evaluate(0, 100, random_source=source((light - 1) / 10, (dark - 1) / 10))
                self.assertEqual(result["predominance"], predominance)
                self.assertEqual(result["predominance_delta"], delta)
                self.assertEqual(result["predominance_intensity"], intensity)

    def test_all_resonances_have_canonical_names(self):
        self.assertEqual(set(RESONANCES), set(range(1, 11)))
        for face, resonance in RESONANCES.items():
            with self.subTest(face=face):
                result = evaluate(0, 100, random_source=source((face - 1) / 10, (face - 1) / 10))
                self.assertTrue(result["resonance"])
                self.assertEqual(result["resonance_value"], face)
                self.assertEqual(result["resonance_name"], resonance["name"])
                self.assertEqual(result["resonance_opening"], resonance["opening"])

    def test_resonance_does_not_replace_success_or_failure_grade(self):
        success = evaluate(0, 14, random_source=source(0.6, 0.6))
        failure = evaluate(0, 15, random_source=source(0.6, 0.6))
        self.assertTrue(success["resonance"])
        self.assertTrue(success["success"])
        self.assertEqual(success["grade"], "success")
        self.assertTrue(failure["resonance"])
        self.assertFalse(failure["success"])
        self.assertEqual(failure["grade"], "failure")

    def test_invalid_bounds(self):
        for modifier, difficulty in [(-1001, 15), (1001, 15), (0, 0), (0, 1001)]:
            with self.subTest(modifier=modifier, difficulty=difficulty):
                with self.assertRaises(RollError):
                    evaluate(modifier, difficulty)

    def test_action_calculates_base_circumstance_and_shared_impulse_cap(self):
        action = prepare_action({
            "action_label": "Examinar inscrição",
            "attribute": {"name": "intelecto", "value": 3},
            "skill": {"name": "conhecimento", "value": 2},
            "impulse": {"level": 1, "reason": "ferramenta adequada"},
            "pressure": {"level": 1, "reason": "sob vigilância"},
            "helpers": [{"label": "A", "reason": "luz"}, {"label": "B", "reason": "mapa"}],
        })
        self.assertEqual(set(ATTRIBUTES), {"corpo", "agilidade", "intelecto", "presenca", "vontade", "sintonia"})
        self.assertEqual(action["base_modifier"], 5)
        self.assertEqual(action["impulse"]["bonus"], 4)
        self.assertEqual(action["pressure"]["penalty"], -2)
        self.assertEqual(action["circumstance_modifier"], 2)
        self.assertEqual(action["modifier_total"], 7)
        self.assertEqual(action["helper_count"], 2)

    def test_action_circumstance_cancellation_and_invalid_levels(self):
        base = {"action_label": "Ação", "attribute": {"name": "corpo", "value": 1},
                "skill": {"name": "atletismo", "value": 1}}
        for impulse, pressure, expected in [(1, 1, 0), (2, 1, 2), (1, 2, -2), (0, 2, -4)]:
            with self.subTest(impulse=impulse, pressure=pressure):
                action = prepare_action({**base, "impulse": {"level": impulse}, "pressure": {"level": pressure}})
                self.assertEqual(action["circumstance_modifier"], expected)
        for invalid in [
            {"helpers": [{}, {}, {}]},
            {"impulse": {"level": 3}},
            {"pressure": {"level": -1}},
        ]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(RollError):
                    prepare_action({**base, **invalid})

    def test_difficulty_presets_leave_custom_values_open(self):
        self.assertEqual(list(DIFFICULTY_PRESETS), [10, 12, 15, 18, 21, 24, 27, 30])
        self.assertEqual(DIFFICULTY_PRESETS[15], "incerta")
        self.assertEqual(evaluate(0, 31, random_source=source(0, 0))["difficulty"], 31)
