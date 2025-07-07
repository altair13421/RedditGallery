from django.db import models

# Create your models here.

class SubReddit(models.Model):
    name = models.CharField(max_length=511, blank=True)
    direct_url = models.URLField(blank=True, null=True)
    sub_reddit = models.CharField(max_length=511, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

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
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def check_deleted(self):
        """
        Check if the image is deleted by looking for a Deleted entry with the same reddit_id.
        """
        return Deleted.objects.filter(image=self).exists()


class Deleted(models.Model):
    subreddit = models.ForeignKey(SubReddit, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)
    gallery = models.ForeignKey(Gallery, on_delete=models.SET_NULL, null=True, blank=True)
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    title = models.CharField(max_length=255, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reddit_id} - {self.title}"

class Settings(models.Model):
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    @staticmethod
    def get_settings():
        try:
            return Settings.objects.first()
        except Settings.DoesNotExist:
            return None
