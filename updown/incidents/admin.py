from django.contrib import admin

from incidents.models import Incident, Report

admin.site.register(Incident)
admin.site.register(Report)
