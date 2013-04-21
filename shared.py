from django.shortcuts import redirect

import flickrapi
from flickrstats.keys import FLICKR

from website.models import *

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

def get_flickr(account):
    return flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                               token = account.token, store_token = False)

def with_account(fn):
    def wrapped(*args, **kwargs):
        request = args[0]

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

        kwargs["account"] = account
        return fn(*args, **kwargs)

    return wrapped
