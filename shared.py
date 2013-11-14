from django.shortcuts import redirect

from datetime import datetime, date, timedelta

import flickrapi
from flickrstats.keys import FLICKR

from website.models import *

def to_epoch(source):
    epoch = date(1970, 1, 1)
    return int((source - epoch).total_seconds()) * 1000

def from_epoch(epoch):
    return datetime.utcfromtimestamp(epoch / 1000).date

def get_account(request):
    try:
        if "account" in request.session:
            return Account.objects.get(user = request.user, nsid = request.session["account"])
    except Account.DoesNotExist:
        pass
    accounts = Account.objects.filter(user = request.user)
    if len(accounts):
        return accounts[0]
    return None

def get_date_range(request):
    if "mindate" in request.GET and "maxdate" in request.GET:
        range = (int(request.GET["mindate"]), int(request.GET["maxdate"]))
        request.session["range"] = range
        return (from_epoch(range[0]), from_epoch(range[1]))

    if "range" in request.session:
        range = request.session["range"]
        return (from_epoch(range[0]), from_epoch(range[1]))

    now = datetime.utcnow()
    lastday = date(now.year, now.month, now.day) - timedelta(1)
    firstday = lastday - timedelta(30)

    range = (to_epoch(firstday), to_epoch(lastday))
    request.session["range"] = range
    return range

def get_flickr(account):
    return flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                               token = account.token, store_token = False)

def with_account(fn):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect("index")

        account = get_account(request)

        if not account:
            return redirect("connect")

        if "account" not in request.session:
            flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                         token = account.token, store_token = False)
            try:
                flickr.auth_checkToken()
                request.session["account"] = account.nsid
            except:
                return redirect("reconnect")

        return fn(request, account, *args, **kwargs)

    return wrapped
