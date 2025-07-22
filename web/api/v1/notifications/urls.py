from django.urls import re_path
from .views import notification_list, notification_detail

urlpatterns = [
    re_path(r'^$', notification_list,
        name='api-notification-list'),
    re_path(r'^(?P<pk>[0-9]+)/$', notification_detail,
        name='api-notification-detail'),
]
