from django.conf.urls import patterns, url

from website import views
from website import json

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^external/frob$', views.frob),

    url(r'^json/visits$', json.visits, name='visits')
)
