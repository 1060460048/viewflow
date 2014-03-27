from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import TemplateView


admin.autodiscover()


urlpatterns = patterns('',  # NOQA
    url(r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^samples/shipment/', include('examples.shipment.urls')),
    url(r'^samples/helloworld/', include('examples.helloworld.urls')),
    url(r'^', include('examples.website')),
)
