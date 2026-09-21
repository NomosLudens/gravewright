from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('', views.gate, name='gate'),
    path('setup', views.access, {'mode': 'setup'}, name='setup'),
    path('login', views.access, {'mode': 'login'}, name='login'),
    path('login/player', views.access, {'mode': 'player'}, name='player-login'),
    path('register', views.access, {'mode': 'register'}, name='register'),
    path('logout', views.browser_logout, name='logout'),
    path('sso/kallistis', views.kallistis_handoff, name='kallistis-handoff'),
    path('api/internal/kallistis/provision/mesa', views.kallistis_provision,
         name='kallistis-provision-mesa'),
    path('api/internal/kallistis/campaigns/list', views.kallistis_campaign_list,
         name='kallistis-campaign-list'),
    path('api/internal/kallistis/campaigns/link', views.kallistis_campaign_link,
         name='kallistis-campaign-link'),
    path('api/kallistis/characters/<str:character_id>', views.kallistis_character_read,
         name='kallistis-character-read'),
    path('api/security/csrf', views.csrf, name='csrf'),
    path('__gravewright/csrf', views.csrf),
    path('api/auth/status', views.status, name='status'),
    path('api/auth/session', views.session, name='session'),
    path('api/auth/setup', views.api_access, {'mode': 'setup'}),
    path('api/auth/register', views.api_access, {'mode': 'register'}),
    path('api/auth/login', views.api_access, {'mode': 'login'}),
    path('api/auth/player-login', views.api_access, {'mode': 'player'}),
    path('api/auth/logout', views.api_logout),
    path('api/auth/account', views.account),
    path('api/home/<str:kind>', views.home, name='home'),
]
