from unittest import TestCase

from gravewright.dice.engine import RollError
from gravewright.dice.kallistis import (
    DARK_PRINCIPLES,
    LIGHT_PRINCIPLES,
    RESONANCES,
    evaluate,
)


def source(*values):
    return iter(values).__next__


class KallistisEngineTests(TestCase):
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
