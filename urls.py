from django.conf.urls import patterns, url

from website import views
from website import data

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),

    # Authenticated pages
    url(r'^dashboard$', views.dashboard, name='dashboard'),

    # Flickr authentication
    url(r'^connect$', views.connect, name='connect'),
    url(r'^reconnect$', views.reconnect, name='reconnect'),
    url(r'^external/frob$', views.frob),

    # JSON data
    url(r'^json/visits$', data.visits, name='visits'),
)
