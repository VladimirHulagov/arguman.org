from django.urls import re_path
from .views import public_newsfeed, private_newsfeed


urlpatterns = [
    re_path(r'^public/$', public_newsfeed, name='api-public-newfeed'),
    re_path(r'^private/$', private_newsfeed, name='api-private-newfeed'),
]
