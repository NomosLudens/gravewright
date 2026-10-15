from django.db import migrations


def correct_knossos_ambush_source(apps, schema_editor):
    Definition = apps.get_model("gravewright_combat", "MissionDefinition")
    definition = Definition.objects.filter(key="knossos-evacuation", version=1).first()
    if not definition:
        return
    content = dict(definition.content)
    technique = dict(content.get("technique", {}))
    eligibility = dict(technique.get("eligibility", {}))
    eligibility["activeProfession"] = "Batedor"
    technique["eligibility"] = eligibility
    technique["implementationStatus"] = (
        "SERVER_ATTACK_VALIDATION_AND_CONDITION_IMPLEMENTED; "
        "DAMAGE_PIPELINE_AND_GODOT_FEEDBACK_PENDING"
    )
    content["technique"] = technique
    definition.content = content
    definition.save(update_fields=["content"])


class Migration(migrations.Migration):

    dependencies = [
        ("gravewright_combat", "0002_missiondefinition_missioninstance_missionevent_and_more"),
    ]

    operations = [
        migrations.RunPython(correct_knossos_ambush_source, migrations.RunPython.noop),
    ]
