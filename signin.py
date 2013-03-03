#!/usr/bin/env python

import os
import sys

root = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
if root not in sys.path:
    sys.path.insert(0, root)
os.environ['DJANGO_SETTINGS_MODULE'] = 'flickrstats.settings'

import flickrapi
from flickrstats.keys import FLICKR
from django.contrib.auth.models import User
from website.models import *
from datetime import datetime, tzinfo, timedelta
from django.utils.timezone import utc

if len(sys.argv) != 2:
    sys.stderr.write("Usage: signin.py <username>\n")
    sys.exit(1)

user = User.objects.get(username = sys.argv[1])
accounts = Account.objects.filter(user = user)

if accounts:
    sys.stderr.write("User %s is already signed in.\n" % user.username)
    sys.exit(1)

flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'], store_token = False)
(token, frob) = flickr.get_token_part_one(perms = 'read')
if not token: raw_input("Press ENTER after you authorized this program")
token = flickr.get_token(frob)

userinfo = flickr.test_login()
id = userinfo.find('user').attrib['id']
username = userinfo.find('user').find('username').text

person = flickr.people_getInfo(user_id = id)
created = datetime.fromtimestamp(int(person.find('person').find('photos').find('firstdate').text), utc)

account = Account(user = user, nsid = id, username = username, token = token)
account.save()
photostream = PhotoStream(account = account, created = created)
photostream.save()
