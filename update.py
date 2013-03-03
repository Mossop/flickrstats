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
from django.db import transaction
from django.utils import timezone
from website.models import *
from datetime import date, datetime, tzinfo, timedelta
from threading import Thread, Lock
from urllib2 import URLError
from pprint import pformat

DAY = timedelta(1)
LIMIT = timedelta(40)

now = datetime.utcnow()
gmtday = date(now.year, now.month, now.day) - DAY

api_count = 0
api_calls = {}
def call_flickr(flickr, name, **kwargs):
    global api_count, api_calls
    api_count = api_count + 1
    if not name in api_calls:
        api_calls[name] = 1
    else:
        api_calls[name] = api_calls[name] + 1
    method = getattr(flickr, name)
    attempt = 0
    while attempt < 3:
        attempt = attempt + 1
        try:
            return method(**kwargs)
        except URLError as e:
            log("%s attempt %d" % (e, attempt))

def build_method(prefix, suffix, thing, args):
    if type(thing) == PhotoStream:
        name = 'Photostream'
    elif type(thing) == PhotoSet:
        name = 'Photoset'
        args['photoset_id'] = thing.set_id
    elif type(thing) == Collection:
        name = 'Collection'
        args['collection_id'] = thing.collection_id
    elif 'photo_id' in thing:
        name = 'Photo'
        args['photo_id'] = thing['photo_id']
    else:
        raise Exception("Unknown type")

    return prefix + name + suffix

def walk_collections(node):
    for item in node:
        if item.tag == 'collection':
            yield item
            for collection in walk_collections(item):
                yield collection

def walk_results(flickr, method, **kwargs):
    count = 0
    page = 1
    pages = 1
    kwargs['per_page'] = 100
    while page <= pages:
        kwargs['page'] = page
        results = call_flickr(flickr, method, **kwargs)
        main = list(results)[0]
        for item in main:
            yield item
        pages = int(main.attrib['pages'])
        page = page + 1

LOGLOCK = Lock()
def log(str):
    LOGLOCK.acquire()
    try:
        print(str)
    finally:
        LOGLOCK.release()

DBLOCK = Lock()
def lockdb(f):
    def locked(*args, **kwargs):
        DBLOCK.acquire()
        try:
            return f(*args, **kwargs)
        finally:
            DBLOCK.release()
    return locked

MAX_THREADS = 20

class ManagedThread(Thread):
    def __init__(self, thread):
        Thread.__init__(self)
        self.thread = thread

    def run(self):
        try:
            self.thread.run()
        finally:
            ThreadManager.thread_complete(self)


class ThreadManager(object):
    thread_count = 0
    pending = []
    lock = Lock()

    @staticmethod
    def add_thread(thread):
        thread = ManagedThread(thread)
        ThreadManager.lock.acquire()
        try:
            if ThreadManager.thread_count < MAX_THREADS:
                ThreadManager.thread_count = ThreadManager.thread_count + 1
                thread.start()
            else:
                ThreadManager.pending.append(thread)
        finally:
            ThreadManager.lock.release()

    @staticmethod
    def thread_complete(thread):
        ThreadManager.lock.acquire()
        try:
            if len(ThreadManager.pending) > 0:
                thread = ThreadManager.pending.pop(0)
                thread.start()
            else:
                ThreadManager.thread_count = ThreadManager.thread_count - 1
                if ThreadManager.thread_count == 0:
                    ThreadManager.complete()
        finally:
            ThreadManager.lock.release()

    @staticmethod
    def complete():
        runtime = datetime.utcnow() - now
        log("Updates complete, took %s with %d API calls" % (runtime, api_count))
        log(pformat(api_calls))

class DateUpdate(object):
    flickr = None
    account = None
    date = None
    sets = None
    collections = None

    dates = None
    domains = None
    referers = None
    visits = None
    photos = None

    def __init__(self, flickr, account, date, sets, collections):
        self.flickr = flickr
        self.account = account
        self.date = date
        self.sets = sets
        self.collections = collections

        self.dates = []
        self.domains = {}
        self.referers = {}
        self.visits = []
        self.photos = []

    def get_stats(self, thing):
        args = {
            'date': self.date
        }
        method = build_method('stats_get', 'Stats', thing, args)
        result = call_flickr(self.flickr, method, **args).find('stats')

        visits = result.attrib['views'] or 0
        comments = 0
        if 'comments' in result.attrib:
            comments = result.attrib['comments'] or 0
        favourites = 0
        if 'favorites' in result.attrib:
            favourites = result.attrib['favorites'] or 0
        self.add_stats(thing, visits, comments, favourites)

    def add_stats(self, thing, visits, comments = 0, favourites = 0):
        self.dates.append({
            'thing': thing,
            'date': self.date,
            'visits': int(visits),
            'comments': int(comments),
            'favourites': int(favourites)
        })
        self.get_domains(thing)

    def get_domains(self, thing):
        args = {
            'date': self.date
        }
        method = build_method('stats_get', 'Domains', thing, args)
        results = walk_results(self.flickr, method, **args)
        for domain in results:
            dbdomain = {
                'name': domain.attrib['name']
            }
            self.domains[domain.attrib['name']] = dbdomain
            self.get_referers(thing, dbdomain)

    def get_referers(self, thing, domain):
        args = {
            'date': self.date,
            'domain': domain['name']
        }
        method = build_method('stats_get', 'Referrers', thing, args)
        results = walk_results(self.flickr, method, **args)
        for referer in results:
            dbreferer = {
                'domain': domain['name'],
                'url': referer.attrib['url'],
                'searchterm': None
            }
            if 'searchterm' in referer.attrib:
                dbreferer['searchterm'] = referer.attrib['searchterm']
            self.referers[referer.attrib['url']] = dbreferer

            count = int(referer.attrib['views'])
            self.visits.append({
                'thing': thing,
                'referer': referer.attrib['url'],
                'date': self.date,
                'count': count
            })

    @lockdb
    def get_photo(self, photo_id):
        return Photo.objects.get(photo_id = photo_id)

    @lockdb
    @transaction.commit_on_success
    def write_data(self):
        # Add any new photos
        for photo in self.photos:
            if 'db' in photo:
                continue
            try:
                photo['db'] = Photo.objects.get(photo_id = photo['photo_id'])
            except Photo.DoesNotExist:
                photo['db'] = Photo(**photo)
                photo['db'].save()

        # domains
        for (name, domain) in self.domains.items():
            db, created = Domain.objects.get_or_create(**domain)
            self.domains[name] = db

        # referers
        for (url, referer) in self.referers.items():
            referer['domain'] = self.domains[referer['domain']]
            db, created = Referer.objects.get_or_create(url = url,
                                                   defaults = {'domain': referer['domain'], 'searchterm': referer['searchterm']})
            self.referers[url] = db

        # visits
        for visit in self.visits:
            if type(visit['thing']) == dict:
                visit['thing'] = visit['thing']['db']
            visit['referer'] = self.referers[visit['referer']]
            dbvisit = Visit(**visit)
            dbvisit.save()

        # dates
        for date in self.dates:
            if type(date['thing']) == dict:
                date['thing'] = date['thing']['db']
            dbdate = Date(**date)
            dbdate.save()

    def run(self):
        log("Updating %s for %s" % (self.account, self.date))
        start = timezone.now()
        totals = call_flickr(self.flickr, 'stats_getTotalViews', date = self.date)
        totals = totals.find('stats')

        # photostream
        photostream = self.account.photostream
        visits = totals.find('photostream').attrib['views']
        self.add_stats(photostream, visits)

        # collections (broken???)
        #for collection in self.collections:
        #    self.get_stats(collection)

        # photosets
        for set in self.sets:
            self.get_stats(set)

        # photos
        photos = walk_results(self.flickr, 'stats_getPopularPhotos', date = self.date)
        for photo in photos:
            # Some photos come through with no ID or any info???
            if not photo.attrib['id']:
                continue
            dbphoto = {
                'account': self.account,
                'photo_id': photo.attrib['id'],
            }
            try:
                indb = self.get_photo(photo.attrib['id'])
                dbphoto['db'] = indb
            except Photo.DoesNotExist:
                fullphoto = call_flickr(self.flickr, 'photos_getInfo', photo_id = photo.attrib['id']).find('photo')
                dbphoto['created'] = datetime.fromtimestamp(int(fullphoto.attrib['dateuploaded']), timezone.utc)
            self.photos.append(dbphoto)
            stats = photo.find('stats')
            self.add_stats(dbphoto,
                           stats.attrib['views'] or 0,
                           stats.attrib['comments'] or 0,
                           stats.attrib['favorites'] or 0)

        self.write_data()
        total = timezone.now() - start
        log("Updating %s for %s took %s" % (self.account, self.date, total))

class AccountUpdate(object):
    account = None
    max_date = None
    flickr = None
    collections = []
    sets = []

    def __init__(self, account, max_date):
        self.account = account
        self.max_date = max_date

    @lockdb
    @transaction.commit_on_success
    def build_lists(self):
        # Build a list of all collections
        self.collections = []
        for collection in walk_collections(call_flickr(self.flickr, 'collections_getTree').find('collections')):
            dbcollection = None
            try:
                dbcollection = Collection.objects.get(collection_id = collection.attrib['id'])
            except Collection.DoesNotExist:
                collection = call_flickr(self.flickr, 'collections_getInfo', collection_id = collection.attrib['id']).find('collection')
                created = datetime.fromtimestamp(int(collection.attrib['datecreate']), timezone.utc)
                dbcollection = Collection(account = self.account, collection_id = collection.attrib['id'], created = created)
                dbcollection.save()
            self.collections.append(dbcollection)

        # Build a list of all sets
        self.sets = []
        for set in walk_results(self.flickr, 'photosets_getList'):
            dbset = None
            try:
                dbset = PhotoSet.objects.get(set_id = set.attrib['id'])
            except PhotoSet.DoesNotExist:
                created = datetime.fromtimestamp(int(set.attrib['date_create']), timezone.utc)
                dbset = PhotoSet(account = self.account, set_id = set.attrib['id'], created = created)
                dbset.save()
            self.sets.append(dbset)

    def run(self):
        self.flickr = flickrapi.FlickrAPI(FLICKR['key'], FLICKR['secret'],
                                     token = account.token, store_token = False)
        call_flickr(self.flickr, 'auth_checkToken')
        self.build_lists()

        photostream = account.photostream
        current = self.max_date
        min_date = current - LIMIT
        while (current >= min_date):
            if not Date.objects.filter(thing = photostream, date = current).exists():
                ThreadManager.add_thread(DateUpdate(self.flickr, self.account, current, self.sets, self.collections))
            current = current - DAY

for account in Account.objects.all():
    ThreadManager.add_thread(AccountUpdate(account, gmtday))
