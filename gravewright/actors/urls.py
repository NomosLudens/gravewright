from django.urls import path

from . import views

urlpatterns = [
    path("api/kallistis/import/options", views.kallistis_import_options),
    path("api/kallistis/import/preview", views.kallistis_import_preview),
    path("api/kallistis/import/confirm", views.kallistis_import_confirm),
    path("api/containers/<uuid:campaign_id>/actors", views.state),
    path("api/containers/<uuid:campaign_id>/actors/<uuid:actor_id>/sheet", views.sheet),
    path("api/containers/<uuid:campaign_id>/actor-upload", views.upload),
    path("game/actors/asset/<uuid:asset_id>", views.asset),
]
