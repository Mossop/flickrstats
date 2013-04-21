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

    filter = {
        "thing__account": account,
        "date__gte": range[0],
        "date__lte": range[1],
    }

    dates = dict()
    data = []

    visits = Date.objects.filter(**filter).values("date", "thing__type") \
                 .annotate(visits = Sum("visits"), comments = Sum("comments"), favourites = Sum("favourites"))
    for visit in visits:
        if visit["date"] in dates:
            date = dates[visit["date"]]
        else:
            date = {
                "date": to_epoch(visit["date"]),
                "comments": 0,
                "favourites": 0,
            }
            dates[visit["date"]] = date
            data.append(date)
        date[visit["thing__type"].lower()] = visit["visits"]
        date["comments"] = date["comments"] + visit["comments"]
        date["favourites"] = date["favourites"] + visit["favourites"]

    return jsonify(data)
