from django.urls import re_path, include
from .users.views import profile_me


urlpatterns = [
    re_path(r'^auth/', include('api.v1.auth.urls')),
    re_path(r'^user/$', profile_me, name='api-me'),
    re_path(r'^users/', include('api.v1.users.urls')),
    re_path(r'^arguments/', include('api.v1.arguments.urls')),
    re_path(r'^newsfeed/', include('api.v1.newsfeed.urls')),
    re_path(r'^notifications/', include('api.v1.notifications.urls')),
]
