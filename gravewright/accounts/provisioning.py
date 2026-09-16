from uuid import UUID

from django.db import transaction

from gravewright.campaigns.models import Campaign, KallistisCampaignLink, Membership

from .models import KallistisIdentity, User


PROVISION_SCHEMA = "kallistis.gravewright.mesa-provision.v1"
TECHNICAL_OWNER_EMAIL = "kallistis-system@shadow.gravewright.invalid"


class KallistisProvisionError(Exception):
    def __init__(self, code, status=400):
        self.code = code
        self.status = status
        super().__init__(code)


def _uuid(value, code):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise KallistisProvisionError(code) from None


def _text(value, code, minimum, maximum):
    if not isinstance(value, str):
        raise KallistisProvisionError(code)
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise KallistisProvisionError(code)
    return value


def parse_payload(payload):
    if not isinstance(payload, dict) or payload.get("schema") != PROVISION_SCHEMA:
        raise KallistisProvisionError("invalid_provision_payload")
    mesa = payload.get("mesa")
    if not isinstance(mesa, dict) or set(mesa) != {"source_system", "source_mesa_id", "name"}:
        raise KallistisProvisionError("invalid_provision_payload")
    if mesa.get("source_system") != "kallistis":
        raise KallistisProvisionError("invalid_source_system")
    mesa_id = _uuid(mesa.get("source_mesa_id"), "invalid_mesa_id")
    mesa_name = _text(mesa.get("name"), "invalid_mesa_name", 1, 80)
    members = payload.get("members")
    if not isinstance(members, list) or not 1 <= len(members) <= 128:
        raise KallistisProvisionError("invalid_members")
    parsed_members = []
    seen = set()
    for member in members:
        if not isinstance(member, dict) or set(member) != {"source_user_id", "display_name", "role"}:
            raise KallistisProvisionError("invalid_member")
        user_id = _uuid(member.get("source_user_id"), "invalid_member_id")
        if user_id in seen:
            raise KallistisProvisionError("duplicate_member")
        seen.add(user_id)
        role = member.get("role")
        if role not in ("mestre", "jogador"):
            raise KallistisProvisionError("invalid_member_role")
        parsed_members.append({
            "source_user_id": str(user_id),
            "display_name": _text(member.get("display_name"), "invalid_display_name", 2, 80),
            "role": role,
        })
    return mesa_id, mesa_name, parsed_members


def _technical_owner():
    owner = User.objects.filter(role=User.Role.OWNER).order_by("date_joined", "id").first()
    if owner is not None:
        return owner
    owner = User(
        name="KALLISTIS System",
        email=TECHNICAL_OWNER_EMAIL,
        role=User.Role.OWNER,
        is_staff=False,
        is_superuser=False,
    )
    owner.set_unusable_password()
    owner.save(force_insert=True)
    return owner


def _identity(member):
    source_user_id = member["source_user_id"]
    identity = KallistisIdentity.objects.select_for_update().filter(
        source_system="kallistis", source_user_id=source_user_id
    ).select_related("user").first()
    if identity is None:
        user = User(
            name=member["display_name"],
            email="kallistis-" + source_user_id + "@shadow.gravewright.invalid",
            role=User.Role.PARTICIPANT,
        )
        user.set_unusable_password()
        user.save(force_insert=True)
        identity = KallistisIdentity.objects.create(
            user=user, source_system="kallistis", source_user_id=source_user_id
        )
    else:
        user = identity.user
        updates = []
        if user.name != member["display_name"]:
            user.name = member["display_name"]
            updates.append("name")
        if not user.is_active:
            user.is_active = True
            updates.append("is_active")
        if user.has_usable_password():
            user.set_unusable_password()
            updates.append("password")
        if updates:
            user.save(update_fields=updates)
    return user


@transaction.atomic
def provision(payload):
    mesa_id, mesa_name, members = parse_payload(payload)
    link = KallistisCampaignLink.objects.select_for_update().filter(
        source_system="kallistis", source_mesa_id=mesa_id
    ).first()
    if link is None:
        campaign = Campaign.objects.create(owner=_technical_owner(), name=mesa_name)
        KallistisCampaignLink.objects.create(
            source_system="kallistis", source_mesa_id=mesa_id, campaign=campaign
        )
        campaign_created = True
    else:
        campaign = Campaign.objects.select_for_update().get(pk=link.campaign_id)
        if campaign.name != mesa_name:
            campaign.name = mesa_name
            campaign.save(update_fields=["name", "updated_at"])
        campaign_created = False

    member_ids = set()
    members_created = 0
    members_updated = 0
    for member in members:
        user = _identity(member)
        member_ids.add(user.pk)
        role = Membership.Role.GM if member["role"] == "mestre" else Membership.Role.PLAYER
        membership = Membership.objects.filter(campaign=campaign, user=user).first()
        if membership is None:
            Membership.objects.create(campaign=campaign, user=user, role=role)
            members_created += 1
        else:
            if membership.role != role:
                membership.role = role
                membership.save(update_fields=["role"])
            members_updated += 1

    stale = Membership.objects.filter(
        campaign=campaign,
        user__kallistis_identity__source_system="kallistis",
    ).exclude(user_id__in=member_ids)
    members_removed = stale.count()
    stale.delete()
    return {
        "valid": True,
        "source_mesa_id": str(mesa_id),
        "campaign_id": str(campaign.pk),
        "campaign_created": campaign_created,
        "campaign_reused": not campaign_created,
        "members_created": members_created,
        "members_updated": members_updated,
        "members_removed": members_removed,
    }
