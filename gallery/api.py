from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import Serializer
from gallery.models import Category, SubReddit, Image, SavedImages
from gallery.serializers import CategorySerializer, ImageSerializer, SubRedditSerializer

from datetime import datetime as dt

class ScanMixin:
    serializer_class: Serializer

    @action(detail=True, methods=["head"])
    def scan_many(self, request, pk=None):
        if self.serializer_class == CategorySerializer:
            ...
        elif self.serializer_class == SubReddit:
            ...


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @action(detail=True, methods=["get"])
    def subreddits(self, request, pk=None):
        category: Category = self.get_object()
        subreddits = category.subs
        serializer = SubRedditSerializer(subreddits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_subreddit(self, request, pk=None): ...

    @action(detail=True, methods=["put"])
    def remove_subreddit(self, request, pk=None): ...

    @action(detail=True, methods=["get"])
    def view(self, request, pk=None): ...


class ImageViewSet(ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    def list(self, request, *args, **kwargs):
        if (category := self.request.GET.get("category", "")) != "":
            subreddits = SubReddit.objects.filter(categories__name=category)
            self.queryset = self.queryset.filter(subreddit__in=subreddits)
        self.queryset = self.queryset.order_by("-date_added")[:2000]
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'head'])
    def download_image(self):
        object = self.get_object()


router = DefaultRouter("api")

router.register("categories", CategoryViewSet, basename="category_viewset")
router.register("images", ImageViewSet, basename="image_viewset")

urlpatterns = [] + router.urls
