from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

import flickrapi
from flickrstats.keys import FLICKR
from website.models import *

def index(request):
    if request.user.is_authenticated():
        accounts = Account.objects.filter(user = request.user)

        if len(accounts):
            account = accounts[0]

            flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                         token = account.token, store_token = False)
            try:
                flickr.auth_checkToken()
                context = {
                    "account": account
                }
                return render(request, "dashboard.html", context)
            except:
                context = {
                    "link": flickr.web_login_url("read")
                }
                return render(request, "reconnect.html", context)
        else:
            flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                         store_token = False)
            context = {
                "link": flickr.web_login_url("read")
            }
            return render(request, "connect.html", context)
    else:
        return render(request, "index.html")

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

    return redirect("index")
