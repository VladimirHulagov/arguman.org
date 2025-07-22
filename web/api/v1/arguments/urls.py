from django.urls import re_path
from .views import (contention_list, contention_detail, premise_detail,
                    premises_list, premise_report, premise_support,
                    premise_supporters)

urlpatterns = [
    re_path(r'^$', contention_list,
        name='api-contention-list'),
    re_path(r'^(?P<pk>[0-9]+)/$', contention_detail,
        name='api-contention-detail'),
    re_path(r'^(?P<pk>[0-9]+)/premises/$', premises_list,
        name='api-contention-premises'),
    re_path(r'^(?P<pk>[0-9]+)/premises/(?P<premise_id>[0-9]+)/$',
        premise_detail, name='api-premise-detail'),
    re_path(r'^(?P<pk>[0-9]+)/premises/(?P<premise_id>[0-9]+)/report/$',
        premise_report, name='api-premise-detail'),
    re_path(r'^(?P<pk>[0-9]+)/premises/(?P<premise_id>[0-9]+)/support/$',
        premise_support, name='api-premise-detail'),
    re_path(r'^(?P<pk>[0-9]+)/premises/(?P<premise_id>[0-9]+)/supporters/$',
        premise_supporters, name='api-premise-supporters'),
]
