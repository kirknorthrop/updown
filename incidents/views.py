from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from incidents.models import Report


def detail(request):
    issues = Report.objects.all().distinct("station")

    return render(request, "main_page.html", {"issues": issues, "resolved": issues})

@method_decorator(csrf_exempt, name='dispatch')
class UpdateIncidentsView(View):

    def post(self, request, *args, **kwargs):
        if request.POST.get("key") == settings.FUNCTIONS_SECRET_KEY:
            call_command("update_incidents")
            return HttpResponse(status=204)
        return HttpResponseNotFound()
