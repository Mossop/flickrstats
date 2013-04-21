from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    user = models.ForeignKey(User)
    nsid = models.TextField(unique = True)
    username = models.TextField()
    token = models.TextField()
    last_update = models.DateField(null = True)

    @property
    def photostream(self):
        return PhotoStream.objects.get(account = self)

    def __unicode__(self):
        return self.username

class Thing(models.Model):
    account = models.ForeignKey(Account)
    created = models.DateTimeField()

class PhotoStream(Thing):
    def __unicode__(self):
        return "%s's photostream" % self.account

class Photo(Thing):
    photo_id = models.TextField(unique = True)

class PhotoSet(Thing):
    set_id = models.TextField(unique = True)

class Collection(Thing):
    collection_id = models.TextField(unique = True)

class Domain(models.Model):
    name = models.TextField(unique = True)

    def __unicode__(self):
        return self.name

class Referer(models.Model):
    domain = models.ForeignKey(Domain)
    url = models.TextField(unique = True)
    searchterm = models.TextField(null = True)

    def __unicode__(self):
        return self.url

class Visit(models.Model):
    thing = models.ForeignKey(Thing, related_name = "visits")
    referer = models.ForeignKey(Referer)
    date = models.DateField()
    count = models.PositiveIntegerField(default = 0)

    class Meta:
        unique_together = ("thing", "referer", "date")

class Date(models.Model):
    thing = models.ForeignKey(Thing, related_name = "dates")
    date = models.DateField()
    visits = models.PositiveIntegerField(default = 0)
    comments = models.PositiveIntegerField(default = 0)
    favourites = models.PositiveIntegerField(default = 0)

    class Meta:
        unique_together = ("thing", "date")
