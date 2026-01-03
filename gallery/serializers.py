# serializers.py

from rest_framework import serializers
from .models import (
    SubReddit, Post, Gallery, Image, Deleted, Category, Settings, IgnoredPosts,
    SavedImages, MainSettings
)

class SubRedditSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubReddit
        fields = ['id', 'name', 'display_name', 'sub_reddit', 'is_active', 'excluded', 'added_on', 'updated_on']


class PostSerializer(serializers.ModelSerializer):
    subreddit = SubRedditSerializer(read_only=True)
    author_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'reddit_id', 'link', 'author', 'title', 'content', 'score',
            'date_added', 'subreddit', 'author_url', 'check_deleted'
        ]

    def get_author_url(self, obj):
        return f"https://www.reddit.com/user/{obj.author}" if obj.author else None


class GallerySerializer(serializers.ModelSerializer):
    subreddit = SubRedditSerializer(read_only=True)

    class Meta:
        model = Gallery
        fields = ['id', 'reddit_id', 'link', 'subreddit']


class ImageSerializer(serializers.ModelSerializer):
    subreddit = SubRedditSerializer(read_only=True)
    # post_ref = PostSerializer(read_only=True)
    gallery = GallerySerializer(read_only=True)

    class Meta:
        model = Image
        fields = [
            'id', 'reddit_id', 'link', 'date_added', 'subreddit',
            'gallery', 'check_deleted'
        ]

class MultiImageView(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = [
            'id', 'reddit_id', 'link', 'date_added', 'subreddit', 'post_ref',
            'gallery', 'check_deleted'
        ]


class DeletedSerializer(serializers.ModelSerializer):
    subreddit = SubRedditSerializer(read_only=True)
    image = ImageSerializer(read_only=True)
    gallery = GallerySerializer(read_only=True)

    class Meta:
        model = Deleted
        fields = [
            'id', 'reddit_id', 'link', 'title', 'date_added', 'subreddit',
            'image', 'gallery'
        ]


class CategorySerializer(serializers.ModelSerializer):
    subs = SubRedditSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'subs']


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ['client_id', 'client_secret', 'user_agent']


class IgnoredPostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = IgnoredPosts
        fields = ['reddit_id']


class SavedImagesSerializer(serializers.ModelSerializer):
    image = ImageSerializer(read_only=True)
    subreddit = SubRedditSerializer(read_only=True)

    class Meta:
        model = SavedImages
        fields = [
            'id', 'image', 'reddit_id', 'link', 'downloaded_at', 'date_added',
            'subreddit'
        ]


class MainSettingsSerializer(serializers.ModelSerializer):
    excluded_subs = serializers.SerializerMethodField()

    class Meta:
        model = MainSettings
        fields = [
            'client_id', 'client_secret', 'user_agent', 'excluded_subreddits',
            'downloads_folder', 'excluded_subs'
        ]

    def get_excluded_subs(self, obj):
        return obj.excluded_subs
