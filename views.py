from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

import flickrapi
from flickrstats.keys import FLICKR

from website.models import *
from website.shared import with_account, get_date_range

def index(request):
    if request.user.is_authenticated():
        return redirect("dashboard")
    return render(request, "index.html")

@with_account
def dashboard(request, account):
    context = {
        "account": account,
        "daterange": get_date_range(request)
    }
    return render(request, "dashboard.html", context)

@login_required
def connect(request):
    flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                 store_token = False)
    context = {
        "link": flickr.web_login_url("read")
    }
    return render(request, "connect.html", context)

@login_required
def reconnect(request):
    flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                 store_token = False)
    context = {
        "link": flickr.web_login_url("read")
    }
    return render(request, "reconnect.html", context)

@login_required
def frob(request):
    frob = request.GET['frob']
    flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                 store_token = False)
    token = flickr.get_token(frob)

    userinfo = flickr.test_login()
    id = userinfo.find('user').attrib['id']
    username = userinfo.find('user').find('username').text

    account, created = Account.objects.get_or_create(user = request.user, nsid = id, username = username)
    account.token = token
    account.save()

    request.session["account"] = id

    return redirect("dashboard")
