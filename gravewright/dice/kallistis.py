"""KALLISTIS core resolution on top of the native server-side dice pipeline."""

from .engine import RollError
from .grammar.runtime import secure_sample


MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 1000
MIN_MODIFIER = -1000
MAX_MODIFIER = 1000


def _validate(modifier, difficulty):
    if type(modifier) is not int or not MIN_MODIFIER <= modifier <= MAX_MODIFIER:
        raise RollError("KALLISTIS modifier must be an integer between -1000 and 1000.")
    if type(difficulty) is not int or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        raise RollError("KALLISTIS difficulty must be an integer between 1 and 1000.")


def _die(random_source):
    sample = random_source()
    if type(sample) not in (int, float) or not 0 <= sample < 1:
        raise RollError("Random source must return a finite value in [0, 1).")
    return int(sample * 10) + 1


def _degree(margin):
    if margin <= -5:
        return "failure_severe"
    if margin < 0:
        return "failure"
    if margin <= 4:
        return "success"
    if margin <= 9:
        return "success_strong"
    return "success_extraordinary"


def _one(modifier, difficulty, random_source):
    light_die = _die(random_source)
    dark_die = _die(random_source)
    natural_total = light_die + dark_die
    total = natural_total + modifier
    margin = total - difficulty
    resonance = light_die == dark_die
    return {
        "system": "kallistis",
        "version": 1,
        "light_die": light_die,
        "dark_die": dark_die,
        "natural_total": natural_total,
        "modifier": modifier,
        "total": total,
        "difficulty": difficulty,
        "margin": margin,
        "success": total >= difficulty,
        "degree": _degree(margin),
        "predominance": "resonance" if resonance else "light" if light_die > dark_die else "dark",
        "resonance": resonance,
        "resonance_value": light_die if resonance else None,
    }


def evaluate(modifier=0, difficulty=15, *, repeat=1, random_source=None):
    """Evaluate one or more authoritative KALLISTIS 2d10 tests.

    The two natural d10 values remain separate. Equality is Ressonância; it
    does not trigger another random draw.
    """
    _validate(modifier, difficulty)
    if type(repeat) is not int or not 1 <= repeat <= 12:
        raise RollError("Choose between 1 and 12 independent rolls.")
    source = random_source if random_source is not None else secure_sample
    results = [_one(modifier, difficulty, source) for _ in range(repeat)]
    return results[0] if repeat == 1 else results
