from django.db import models

# Create your models here.

class SubReddit(models.Model):
    name = models.CharField(max_length=511, blank=True)
    direct_url = models.URLField(blank=True, null=True)
    sub_reddit = models.CharField(max_length=511, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)

class Gallery(models.Model):
    subreddit = models.ForeignKey(SubReddit, on_delete=models.SET_NULL, null=True, blank=True)
    link = models.URLField(blank=True)
    title = models.CharField(max_length=511, blank=True)

class Image(models.Model):
    subreddit = models.ForeignKey(SubReddit, on_delete=models.SET_NULL, null=True, blank=True)
    gallery = models.ForeignKey(Gallery, on_delete=models.SET_NULL, null=True, blank=True)
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    title = models.CharField(max_length=255, blank=True)

