from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.http import HttpResponse
from django.db.models import Sum

import datetime

from website.models import *
from website.shared import *

def jsonify(data):
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def toepoch(date):
    return int((date - datetime.date(1970, 1, 1)).total_seconds()) * 1000

def build_visits(account, typename):
    kwargs = {}
    kwargs["thing__" + typename] = None
    visits = Date.objects.filter(thing__account = account).exclude(**kwargs).values("date").annotate(visits = Sum("visits"))
    return [{ "date": toepoch(v["date"]), "visits": v["visits"]} for v in visits]

@with_account
def visits(request, account):
    visits = Date.objects.filter(thing__account = account).values("date").annotate(visits = Sum("visits"))
    data = {
      "photostream": build_visits(account, "photostream"),
      "photos": build_visits(account, "photo"),
      "photosets": build_visits(account, "photoset")
    }
    return jsonify(data)
