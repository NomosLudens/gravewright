import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from gravewright.campaigns.models import KallistisCampaignLink, Membership

from . import services
from .models import KallistisIdentity, User


class KallistisHandoffError(Exception):
    pass


def _remote_handoff(code):
    if not settings.KALLISTIS_VTT_CONSUME_URL or not settings.KALLISTIS_VTT_SERVICE_SECRET:
        raise KallistisHandoffError
    try:
        request = Request(
            settings.KALLISTIS_VTT_CONSUME_URL,
            data=json.dumps({"code": code}).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + settings.KALLISTIS_VTT_SERVICE_SECRET,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Gravewright-KALLISTIS-Bridge/1",
            },
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read(16 * 1024))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        raise KallistisHandoffError from None
    if not isinstance(payload, dict) or payload.get("valid") is not True:
        raise KallistisHandoffError
    return payload


def consume_handoff(request, code):
    if not isinstance(code, str) or not 32 <= len(code) <= 128:
        raise KallistisHandoffError
    payload = _remote_handoff(code)
    try:
        source_user_id = str(UUID(str(payload["user_id"])))
        source_mesa_id = UUID(str(payload["mesa_id"]))
        source_campaign_id = UUID(str(payload["campaign_id"]))
    except (KeyError, TypeError, ValueError):
        raise KallistisHandoffError from None
    source_role = payload.get("role")
    role = {"mestre": Membership.Role.GM, "jogador": Membership.Role.PLAYER}.get(source_role)
    if role is None:
        raise KallistisHandoffError

    link = KallistisCampaignLink.objects.select_related("campaign").filter(
        source_system="kallistis",
        source_mesa_id=source_mesa_id,
        campaign_id=source_campaign_id,
    ).first()
    if link is None:
        raise KallistisHandoffError

    display_name = payload.get("display_name")
    if not isinstance(display_name, str) or len(display_name.strip()) < 2:
        display_name = "KALLISTIS " + source_user_id[:8]
    display_name = display_name.strip()[:80]
    email = "kallistis-" + source_user_id + "@shadow.gravewright.invalid"

    with transaction.atomic():
        identity = KallistisIdentity.objects.select_for_update().filter(
            source_system="kallistis", source_user_id=source_user_id
        ).select_related("user").first()
        if identity is None:
            user = User(name=display_name, email=email, role=User.Role.PARTICIPANT)
            user.set_unusable_password()
            user.save(force_insert=True)
            identity = KallistisIdentity.objects.create(
                user=user, source_system="kallistis", source_user_id=source_user_id
            )
        else:
            user = identity.user
            if user.has_usable_password():
                user.set_unusable_password()
                user.save(update_fields=["password"])
        Membership.objects.update_or_create(
            campaign=link.campaign,
            user=user,
            defaults={"role": role, "joined_at": timezone.now()},
        )
        services.start_session(request, user)
    return link.campaign_id

