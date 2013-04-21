from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.http import HttpResponse
from django.db.models import Sum

import datetime

from website.models import *
from website.views import get_account

def jsonify(data):
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def toepoch(date):
    return int((date - datetime.date(1970, 1, 1)).total_seconds()) * 1000

@login_required
def visits(request):
    account = get_account(request)

    visits = Date.objects.filter(thing__account = account).values("date").annotate(visits = Sum("visits"))
    data = {
      "visits": [{ "date": toepoch(v["date"]), "visits": v["visits"]} for v in visits]
    }
    return jsonify(data)
