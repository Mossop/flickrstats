from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.http import HttpResponse
from django.db.models import Sum

from website.models import *
from website.shared import with_account, get_date_range, to_epoch

def jsonify(data):
    return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def build_visits(account, range, typename):
    filter = {
        "thing__account": account,
        "date__gte": range[0],
        "date__lte": range[1],
    }

    exclude = {}
    exclude["thing__" + typename] = None

    visits = Date.objects.filter(**filter).exclude(**exclude).values("date").annotate(visits = Sum("visits"))
    return [{ "date": to_epoch(v["date"]), "visits": v["visits"]} for v in visits]

@with_account
def visits(request, account):
    range = get_date_range(request)

    data = {
      "photostream": build_visits(account, range, "photostream"),
      "photos": build_visits(account, range, "photo"),
      "photosets": build_visits(account, range, "photoset")
    }
    return jsonify(data)
