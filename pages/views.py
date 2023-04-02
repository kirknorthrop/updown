from django.shortcuts import render
from django.views.generic import TemplateView


class FAQPageView(TemplateView):
    template_name = "faq.html"


class PressPageView(TemplateView):
    template_name = "press.html"


class PrivacyPageView(TemplateView):
    template_name = "privacy.html"
