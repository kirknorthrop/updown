from django.contrib import admin
from django.urls import path

from incidents.views import detail, UpdateIncidentsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", detail),
    path("functions/update_incidents", UpdateIncidentsView.as_view()),
]
