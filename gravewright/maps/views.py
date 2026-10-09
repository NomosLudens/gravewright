import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from gravewright.journals.services import JournalError, member
from . import services
from .models import Scene, Tile


def notify(campaign_id):
    async_to_sync(get_channel_layer().group_send)(
        f"table.{campaign_id.hex}", {"type": "room.maps"}
    )


@require_POST
def upload(request, campaign_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=403)
    try:
        raw_settings = json.loads(request.POST.get("settings", "{}"))
        row = services.create_from_upload(
            campaign_id,
            request.user.pk,
            request.POST.get("name"),
            raw_settings,
            request.FILES.get("map"),
            activate=request.POST.get("activate") == "true",
        )
        notify(campaign_id)
        return JsonResponse(services.view(row), status=201)
    except (services.MapError, JournalError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)


def authorized(request, map_id):
    if not request.user.is_authenticated:
        raise Http404
    row = Scene.objects.filter(pk=map_id).first()
    if row is None:
        raise Http404
    try:
        return services.scene(map_id, member(row.campaign_id, request.user.pk))
    except services.MapError, JournalError:
        raise Http404 from None


@require_GET
def manifest(request, map_id):
    response = JsonResponse(services.manifest(authorized(request, map_id)))
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def tile(request, map_id, lod, x, y):
    row = authorized(request, map_id)
    item = Tile.objects.filter(scene=row, lod=lod, x=x, y=y).first()
    if item is None:
        raise Http404
    try:
        response = FileResponse(item.file.open("rb"), content_type="image/webp")
    except FileNotFoundError:
        raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def state(request, campaign_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        return JsonResponse(services.state(campaign_id, request.user.pk))
    except services.MapError, JournalError:
        raise Http404 from None


@require_GET
def layers(request, map_id):
    from .objects import layer_state

    row = authorized(request, map_id)
    response = JsonResponse(layer_state(row, member(row.campaign_id, request.user.pk)))
    response["Cache-Control"] = "private, no-store"
    return response
