from django.contrib import admin

from incidents.models import Incident, Report

admin.site.register(Incident)
admin.site.register(Report)

admin.site.site_header = 'Up Down London Administration'