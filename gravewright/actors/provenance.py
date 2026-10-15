"""Explicit canonical, local-fixture, and scenario-NPC authority boundaries."""

import os
from pathlib import Path

from django.conf import settings

from .models import KallistisCharacterLink


PROVENANCE_KEY = "gravewright_provenance"
SHEET_KEY = "qa_character_sheet"
PROVENANCE_SCHEMA = "gravewright.actor-provenance.v1"
CANONICAL = "CANONICAL"
NON_CANONICAL = "NON_CANONICAL"


class ProvenanceError(ValueError):
    pass


def qa_fixture_environment_enabled():
    """QA fixture authority requires explicit local settings and confined paths."""
    if getattr(settings, "GRAVEWRIGHT_TACTICAL_QA_FIXTURES_ENABLED", False) is not True:
        return False
    root_value = getattr(settings, "GRAVEWRIGHT_TACTICAL_QA_FIXTURE_ROOT", "")
    if not root_value:
        return False
    root = Path(root_value).resolve()
    if not root.is_relative_to(Path("/tmp").resolve()) or root == Path("/tmp").resolve():
        return False
    database = settings.DATABASES.get("default", {})
    if not database.get("ENGINE", "").endswith("sqlite3"):
        return False
    db_path = Path(database.get("NAME", "")).resolve()
    test_path = Path(database.get("TEST", {}).get("NAME", "")).resolve()
    test_database = db_path == test_path and db_path.name.startswith("test-")
    if not settings.DEBUG and not test_database:
        return False
    media_path = Path(settings.MEDIA_ROOT).resolve()
    try:
        configured_db = Path(os.environ["GRAVEWRIGHT_DATABASE"]).resolve()
    except (KeyError, TypeError):
        return False
    if db_path not in {configured_db, test_path} or not db_path.is_relative_to(root):
        return False
    if not test_path.is_relative_to(root) or not media_path.is_relative_to(root):
        return False
    loopback_hosts = {"127.0.0.1", "localhost", "[::1]"}
    allowed_hosts = loopback_hosts | ({"testserver"} if test_database else set())
    if not settings.ALLOWED_HOSTS or not set(settings.ALLOWED_HOSTS) <= allowed_hosts:
        return False
    # The fixture instance cannot call the federation or marketplace services.
    if any((
        getattr(settings, "KALLISTIS_VTT_CONSUME_URL", ""),
        getattr(settings, "KALLISTIS_VTT_SERVICE_SECRET", ""),
        getattr(settings, "KALLISTIS_VTT_CHARACTER_READ_URL", ""),
        getattr(settings, "KALLISTIS_ORIGIN", ""),
        getattr(settings, "GRAVEWRIGHT_MARKETPLACE_URL", ""),
        getattr(settings, "GRAVEWRIGHT_PUBLIC_ORIGIN", ""),
    )):
        return False
    return True


def canonical_link(actor):
    """Return only source-approved canonical provenance, never a local marker."""
    fields = actor.data.get("fields", {}) if isinstance(actor.data, dict) else {}
    provenance = fields.get(PROVENANCE_KEY) if isinstance(fields, dict) else None
    if isinstance(provenance, dict) and provenance.get("authority") != CANONICAL:
        return None
    return KallistisCharacterLink.objects.filter(
        actor=actor, canonical=True, source_state="approved"
    ).first()


def qa_sheet(actor):
    fields = actor.data.get("fields", {}) if isinstance(actor.data, dict) else {}
    sheet = fields.get(SHEET_KEY) if isinstance(fields, dict) else None
    provenance = fields.get(PROVENANCE_KEY) if isinstance(fields, dict) else None
    if not qa_fixture_environment_enabled():
        return None
    if not isinstance(provenance, dict) or provenance.get("schema") != PROVENANCE_SCHEMA:
        return None
    if provenance.get("authority") != NON_CANONICAL:
        return None
    if provenance.get("category") not in {"qa_fixture", "scenario_npc"}:
        return None
    if KallistisCharacterLink.objects.filter(actor=actor).exists():
        return None
    if not isinstance(sheet, dict) or sheet.get("complete") is not True:
        return None
    if provenance.get("category") == "qa_fixture" and actor.type != "character":
        return None
    return sheet


def validate_qa_sheet(actor):
    """Validate the complete supported mechanical projection for QA records."""
    sheet = qa_sheet(actor)
    if sheet is None:
        return False
    from . import runtime
    from gravewright.combat.kallistis_equipment import WEAPONS

    state = runtime.read(actor.data)
    attrs = sheet.get("attributes")
    skills = sheet.get("skills")
    tracks = sheet.get("tracks")
    equipment = sheet.get("equipment")
    if not isinstance(attrs, dict) or not isinstance(skills, dict):
        return False
    # Freeze v1.3 starting allocation: the six attribute values and skill ranks
    # must stay inside the documented starting budget.
    if set(attrs) != set(runtime.ATTRIBUTE_NAMES) or sorted(attrs.values()) != [0, 1, 1, 2, 2, 3]:
        return False
    if attrs != {key: state["attributes"][key] for key in runtime.ATTRIBUTE_NAMES}:
        return False
    if sheet.get("milestone") != state["attributes"].get("marco"):
        return False
    if set(skills) != set(runtime.SKILL_NAMES) or skills != state["skills"]:
        return False
    ranks = sorted(value for value in skills.values() if value)
    if any(type(value) is not int or not 0 <= value <= runtime.SKILL_MAX for value in skills.values()):
        return False
    if ranks.count(3) != 1 or ranks.count(2) != 3 or ranks.count(1) != 4 or len(ranks) != 8:
        return False
    people = sheet.get("people")
    if not isinstance(people, dict) or state.get("people", {}).get("id") != people.get("id") or state.get("heritage", {}).get("id") != people.get("heritage"):
        return False
    try:
        runtime._people_projection(people)
    except Exception:
        return False
    if not isinstance(tracks, list) or not tracks:
        return False
    active = sheet.get("activeTrack")
    if type(active) is not int or not 0 <= active < len(tracks):
        return False
    track = tracks[active]
    if not isinstance(track, dict) or track.get("profession") not in {"Batedor", "Guardião", "Tecelão", "Médico"}:
        return False
    if type(track.get("milestone")) is not int or not 1 <= track["milestone"] <= 2:
        return False
    techniques = track.get("techniques")
    if not isinstance(techniques, list):
        return False
    if "Emboscada" in techniques and not (track["profession"] == "Batedor" and track["milestone"] >= 2):
        return False
    if not isinstance(equipment, dict) or equipment.get("weapon") not in WEAPONS or equipment.get("proficiencyConfirmed") is not True:
        return False
    if type(sheet.get("protection")) is not int or not 0 <= sheet["protection"] <= 1000:
        return False
    if sheet["protection"] != state["protection"]:
        return False
    sheet_resources = sheet.get("resources")
    runtime_resources = state.get("resources")
    if not isinstance(sheet_resources, dict) or not isinstance(runtime_resources, dict):
        return False
    if set(sheet_resources) != set(runtime_resources):
        return False
    # The sheet records the validated starting maxima. Current values are
    # mutable combat state and must remain legal after attacks or techniques.
    for resource, initial in sheet_resources.items():
        current = runtime_resources.get(resource)
        if not isinstance(initial, dict) or not isinstance(current, dict):
            return False
        initial_max = initial.get("max")
        initial_value = initial.get("current")
        current_value = current.get("current")
        if type(initial_max) is not int or type(initial_value) is not int:
            return False
        if not 0 <= initial_value <= initial_max:
            return False
        if current.get("max") != initial_max:
            return False
        if type(current_value) is not int or not 0 <= current_value <= initial_max:
            return False
    return True


def is_canonical(actor):
    """A QA record can never be interpreted as an approved KALLÍSTIS character."""
    if qa_sheet(actor) is not None:
        return False
    fields = actor.data.get("fields", {}) if isinstance(actor.data, dict) else {}
    provenance = fields.get(PROVENANCE_KEY) if isinstance(fields, dict) else None
    if isinstance(provenance, dict) and provenance.get("authority") == NON_CANONICAL:
        return False
    return canonical_link(actor) is not None
