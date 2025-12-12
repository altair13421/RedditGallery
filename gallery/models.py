from django.db import models
import os
from django.conf import settings

# Create your models here.

from django.db import connection

def reset_connection_pool():
    connection.close()

class SubReddit(models.Model):
    name = models.CharField(max_length=511, blank=True)
    direct_url = models.URLField(blank=True, null=True)
    display_name = models.TextField(blank=True, null=True)
    sub_reddit = models.CharField(max_length=511, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    excluded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sub_reddit} - Active: {self.is_active} - Excluded: {self.excluded}"


class Post(models.Model):
    subreddit = models.ForeignKey(
        SubReddit, on_delete=models.CASCADE, null=True, blank=True
    )
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    author_url = models.URLField(blank=True)
    title = models.CharField(max_length=511, blank=True)
    content = models.TextField(blank=True)
    score = models.IntegerField(default=0)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subreddit.name} - {self.link} - {self.title}"

    def save(self, *args, **kwargs):
        if self.author:
            self.author_url = f"""https://www.reddit.com/user/{self.author}"""
        super().save(*args, **kwargs)

    @property
    def check_deleted(self):
        """
        Check if the post is deleted by looking for a Deleted entry with the same reddit_id.
        """
        return Deleted.objects.filter(post=self).exists()


class Gallery(models.Model):
    post_ref = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    subreddit = models.ForeignKey(
        SubReddit, on_delete=models.SET_NULL, null=True, blank=True
    )
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)

    def __str__(self):
        return f"{self.subreddit} - {self.link}"

class Image(models.Model):
    post_ref = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    subreddit = models.ForeignKey(
        SubReddit, on_delete=models.SET_NULL, null=True, blank=True
    )
    gallery = models.ForeignKey(
        Gallery, on_delete=models.SET_NULL, null=True, blank=True
    )
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return super().__str__() + f" - {self.link} - {self.post_ref} - {self.subreddit}"

    @property
    def check_deleted(self):
        """
        Check if the image is deleted by looking for a Deleted entry with the same reddit_id.
        """
        return Deleted.objects.filter(image=self).exists()


class Deleted(models.Model):
    subreddit = models.ForeignKey(
        SubReddit, on_delete=models.SET_NULL, null=True, blank=True
    )
    image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)
    gallery = models.ForeignKey(
        Gallery, on_delete=models.SET_NULL, null=True, blank=True
    )
    reddit_id = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    title = models.CharField(max_length=255, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reddit_id} - {self.title}"

class Category(models.Model):
    name = models.CharField(max_length=255, blank=True, default="Undefined")
    description = models.TextField(blank=True)
    subreddits = models.ManyToManyField(SubReddit, verbose_name="subreddits", blank=True, related_name="categories")

    def __str__(self):
        return self.name

    @property
    def subs(self):
        return self.subreddits.all()

    @classmethod
    def get_all_categories(cls):
        return cls.objects.all()

    @classmethod
    def get_category_names(cls):
        return [(category.id, category.name) for category in cls.objects.all()]

    @classmethod
    def get_category_by_name(cls, name):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None

    @classmethod
    def add_subreddit_to_category(cls, category_name, subreddit):
        category = cls.get_category_by_name(category_name)
        if category:
            category.subs.add(subreddit)
            category.save()
            return True
        return False

    @classmethod
    def remove_subreddit_from_category(cls, category_name, subreddit):
        category = cls.get_category_by_name(category_name)
        if category:
            category.subs.remove(subreddit)
            category.save()
            return True
        return False

    @classmethod
    def delete_category(cls, name):
        category = cls.get_category_by_name(name)
        if category:
            category.delete()
            return True
        return False

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


class IgnoredPosts(models.Model):
    reddit_id = models.CharField(blank=True, max_length=255)


class SavedImages(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, null=True, blank=True)
    subreddit = models.ForeignKey(
        SubReddit, on_delete=models.SET_NULL, null=True, blank=True
    )
    reddit_id = models.CharField(max_length=255, blank=True)
    downloaded_at = models.FilePathField(blank=True)
    link = models.URLField(blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reddit_id} - {self.link}"


class MainSettings(models.Model):
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    # Other User Settings can be added here
    excluded_subreddits = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated list of subreddits to ignore to view From the gallery.",
    )
    downloads_folder = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Folder where images will be downloaded.",
    )

    @property
    def excluded_subs(self):
        """Return a list of excluded subreddits."""
        if self.excluded_subreddits:
            return [sub.strip() for sub in self.excluded_subreddits.split(",")]
        return []

    @classmethod
    def get_initials(cls):
        instance = cls.get_or_create_settings()
        return {
            "client_id": instance.client_id,
            "client_secret": instance.client_secret,
            "user_agent": instance.user_agent,
            "excluded_subreddits": instance.excluded_subreddits,
            "downloads_folder": instance.downloads_folder,
        }

    @classmethod
    def get_or_create_settings(cls):
        try:
            obj = cls.objects.first()
            if not obj:
                raise cls.DoesNotExist("MainSettings instance does not exist.")
            return obj
        except cls.DoesNotExist:
            # If no settings exist, create a default one
            default_settings = cls()
            default_settings.client_id = settings.CLIENT_ID or ""
            default_settings.client_secret = settings.CLIENT_SECRET or ""
            default_settings.user_agent = settings.USER_AGENT or ""
            if os.name in ["nt", "NT"]:
                default_settings.downloads_folder = "C:\\Downloads"
            else:
                default_settings.downloads_folder = "/downloads"
            default_settings.save()
            default_settings.excluded_subreddits = "announcements, mod, moderators, all, popular, random"
            return default_settings

    def save(self, *args, **kwargs):
        if os.path.exists(self.downloads_folder):
            self.downloads_folder = os.path.abspath(self.downloads_folder)
        else:
            os.makedirs(self.downloads_folder, exist_ok=True)
        super().save(*args, **kwargs)

    def __repr__(self):
        return "MainSettings(client_id={}, client_secret={}, user_agent={}, excluded_subreddits={}, downloads_folder={})".format(
            self.client_id,
            self.client_secret,
            self.user_agent,
            self.excluded_subreddits,
            self.downloads_folder,
        )
