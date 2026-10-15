"""Small, fixed G5.3 actor catalog for a guarded local QA instance."""

from copy import deepcopy

from django.db import transaction

from gravewright.campaigns.models import Membership
from gravewright.maps.services import MapError
from gravewright.pdf_system.schema import normalize

from .models import Actor
from .provenance import (
    NON_CANONICAL,
    PROVENANCE_KEY,
    PROVENANCE_SCHEMA,
    SHEET_KEY,
    qa_fixture_environment_enabled,
    validate_qa_sheet,
)


_FIXTURES = {
    "ally-batedor": ("Aliada QA Batedora", "qa_fixture", "aelvari", "cronista", 2, ["Emboscada"]),
    "ally-guard": ("Aliado QA Guardião", "qa_fixture", "kragor", "escudo_do_cla", 1, []),
    "ally-scout": ("Aliada QA Batedora 2", "qa_fixture", "teriantes", "cacador", 1, []),
    "silmari-1": ("Silmari QA Sentinela 1", "scenario_npc", "kragor", "escudo_do_cla", 1, []),
    "silmari-2": ("Silmari QA Sentinela 2", "scenario_npc", "doreos", "guardiao_de_obra", 1, []),
    "silmari-3": ("Silmari QA Sentinela 3", "scenario_npc", "nimari", "cartografo_de_frestas", 1, []),
    "nomos-evacuee": ("Nomos QA Evacuado", "scenario_npc", "nomos", "reparador", 1, []),
}


def _sheet(people, heritage, milestone, techniques):
    attributes = {
        "corpo": 3, "agilidade": 2, "intelecto": 2,
        "presenca": 1, "vontade": 1, "sintonia": 0,
    }
    skills = {
        "atletismo": 1, "combate": 3, "pontaria": 0,
        "furtividade": 2, "percepcao": 2, "sobrevivencia": 1,
        "investigacao": 1, "conhecimento": 0, "oficio": 0,
        "influencia": 0, "empatia": 0, "cuidado": 0,
        "magia": 0, "evocacao": 0, "velarim": 0,
    }
    skills["atletismo"] = 1
    skills["combate"] = 3
    skills["furtividade"] = 2
    skills["percepcao"] = 2
    skills["sobrevivencia"] = 2
    skills["investigacao"] = 1
    skills["influencia"] = 1
    skills["pontaria"] = 1
    return {
        "schema": "kallistis.character.qa.v1",
        "complete": True,
        "people": {"id": people, "heritage": heritage},
        "attributes": attributes,
        "skills": skills,
        "activeTrack": 0,
        "milestone": milestone,
        "tracks": [{"profession": "Batedor", "milestone": milestone, "techniques": techniques}],
        "equipment": {"weapon": "Faca", "proficiencyConfirmed": True},
        "protection": 0,
    }


@transaction.atomic
def create(who, fixture_key, player_id=None):
    """Create or replay exactly one catalog actor through the campaign service."""
    if who.role != "gm":
        raise MapError("Only the QA campaign GM can provision scenario actors.", "forbidden")
    if not qa_fixture_environment_enabled():
        raise MapError("QA fixtures require the isolated local QA settings.", "qa_fixtures_disabled")
    spec = _FIXTURES.get(fixture_key)
    if not spec:
        raise MapError("Unknown G5.3 fixture key.")
    name, category, people, heritage, milestone, techniques = spec
    permissions = {}
    if category == "qa_fixture":
        player = Membership.objects.filter(
            campaign_id=who.campaign_id, user_id=player_id, role="player", user__is_active=True
        ).first()
        if player is None:
            raise MapError("Ally QA actors require a real player in this campaign.", "invalid_member")
        permissions[str(player.user_id)] = "owner"
    existing = next((
        row for row in Actor.objects.filter(campaign_id=who.campaign_id)
        if isinstance(row.data, dict)
        and isinstance(row.data.get("fields"), dict)
        and isinstance(row.data["fields"].get(PROVENANCE_KEY), dict)
        and row.data["fields"][PROVENANCE_KEY].get("fixture_key") == fixture_key
    ), None)
    if existing:
        if not validate_qa_sheet(existing):
            raise MapError("Existing fixture has drifted from its validated QA profile.", "fixture_conflict")
        return {"id": str(existing.pk), "fixtureKey": fixture_key, "reused": True}
    actor_type = "character"
    actor = Actor.objects.create(
        campaign_id=who.campaign_id,
        name=name,
        type=actor_type,
        permissions=permissions,
        data=normalize({}),
    )
    sheet = _sheet(people, heritage, milestone, techniques)
    from .runtime import initialize

    initialized = initialize({
        "actorId": str(actor.pk),
        "attributes": {**sheet["attributes"], "marco": milestone},
        "skills": sheet["skills"],
        "people": sheet["people"],
        "protection": sheet["protection"],
    }, who)
    actor.refresh_from_db()
    fields = deepcopy(actor.data.get("fields", {}))
    fields.update({
        PROVENANCE_KEY: {
            "schema": PROVENANCE_SCHEMA,
            "category": category,
            "authority": NON_CANONICAL,
            "fixture_key": fixture_key,
            **({"faction": "Silmari"} if category == "scenario_npc" and fixture_key.startswith("silmari-") else {}),
        },
        SHEET_KEY: {**sheet, "resources": initialized["runtime"]["resources"]},
    })
    actor.data["fields"] = fields
    actor.save(update_fields=["data", "updated_at"])
    if not validate_qa_sheet(actor):
        raise MapError("Fixture failed its mechanical provenance validation.", "invalid_fixture")
    return {"id": str(actor.pk), "fixtureKey": fixture_key, "reused": False}
