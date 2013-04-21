from django.shortcuts import redirect

from datetime import datetime, date, timedelta

import flickrapi
from flickrstats.keys import FLICKR

from website.models import *

def to_epoch(source):
    return int((source - date(1970, 1, 1)).total_seconds()) * 1000

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
    if "range" in request.session:
        return request.session["range"]

    now = datetime.utcnow()
    lastday = date(now.year, now.month, now.day) - timedelta(1)
    firstday = lastday - timedelta(30)

    range = (firstday, lastday)
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
