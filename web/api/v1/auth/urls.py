from django.urls import re_path
from rest_framework.authtoken.views import obtain_auth_token
from .views import UserRegisterView


urlpatterns = [
    re_path(r'^login/$', obtain_auth_token, name="api-login"),
    re_path(r'^register/$', UserRegisterView.as_view(), name="api-register"),
]
