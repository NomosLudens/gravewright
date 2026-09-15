from unittest import TestCase

from gravewright.dice.engine import RollError
from gravewright.dice.kallistis import evaluate


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
        self.assertFalse(result["resonance"])

    def test_dark_predominance_and_failure_with_negative_margin(self):
        result = evaluate(0, 15, random_source=source(0.1, 0.8))
        self.assertEqual((result["light_die"], result["dark_die"]), (2, 9))
        self.assertEqual(result["margin"], -4)
        self.assertFalse(result["success"])
        self.assertEqual(result["predominance"], "dark")

    def test_resonance_1_1(self):
        result = evaluate(0, 2, random_source=source(0, 0))
        self.assertEqual((result["light_die"], result["dark_die"]), (1, 1))
        self.assertTrue(result["success"])
        self.assertEqual(result["margin"], 0)
        self.assertEqual(result["predominance"], "resonance")
        self.assertTrue(result["resonance"])
        self.assertEqual(result["resonance_value"], 1)

    def test_resonance_10_10(self):
        result = evaluate(0, 21, random_source=source(0.999999, 0.999999))
        self.assertEqual((result["light_die"], result["dark_die"]), (10, 10))
        self.assertFalse(result["success"])
        self.assertEqual(result["margin"], -1)
        self.assertTrue(result["resonance"])
        self.assertEqual(result["resonance_value"], 10)

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

    def test_invalid_bounds(self):
        for modifier, difficulty in [(-1001, 15), (1001, 15), (0, 0), (0, 1001)]:
            with self.subTest(modifier=modifier, difficulty=difficulty):
                with self.assertRaises(RollError):
                    evaluate(modifier, difficulty)
