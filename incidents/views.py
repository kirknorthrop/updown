from django.shortcuts import render

from incidents.models import Report


def detail(request):

    issues = Report.objects.all().distinct("station")

    return render(request, 'main_page.html', {'issues': issues, 'resolved': issues})
