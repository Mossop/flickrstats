from django.shortcuts import render

from website.models import *

def index(request):
    return render(request, "index.html")
