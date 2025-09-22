import os
from django.db.models.manager import BaseManager
from django.shortcuts import redirect
from django.urls import reverse
import requests

# Create your views here.
from django.views.generic import ListView, View, DetailView, CreateView
from django.http import HttpResponse

from .forms import SettingsForm, SubRedditForm

from .models import IgnoredPosts, Image, MainSettings, Post, SubReddit, SavedImages
from .utils import sync_data, sync_singular, check_if_good_image
from django.db.models import Q
from tqdm import tqdm
from icecream import ic

def get_settings() -> MainSettings:
    return MainSettings.get_or_create_settings()


class FolderOnlyView(DetailView):
    model = SubReddit
    template_name = "gallery.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subreddit: SubReddit = self.get_object()
        images = (
            Image.objects.filter(subreddit=subreddit)
            .select_related()
            .order_by("-date_added")
        )
        context["total_images"] = images.count()
        context["newest_image"] = Image.objects.order_by("-date_added").first()
        context["subs"] = SubReddit.objects.all()
        context["active_sub"] = subreddit.sub_reddit
        context["the_sub"] = subreddit
        context["images"] = images
        return context


class ImageListView(ListView):
    model = Image
    template_name = "gallery.html"
    context_object_name = "images"
    paginate_by = 1000  # Optional pagination

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = Image.objects.count()
        context["newest_image"] = Image.objects.order_by("-date_added").first()
        context["subs"] = SubReddit.objects.all()
        return context

    def get_queryset(self):
        return (
            Image.objects.select_related()
            .exclude(subreddit__excluded=True)
            .order_by("-date_added")
            .all()
        )


class ImageSaveView(View):
    def get(self, request, pk):
        image = Image.objects.get(pk=pk)
        try:
            response = requests.get(image.link, stream=True)
            response.raise_for_status()
            file_path = image.link.split("/")[-1]
            file_path = file_path.split("?")[0]
            FOLDER = f"{get_settings().downloads_folder}/{image.subreddit.sub_reddit}"
            if not os.path.exists(FOLDER):
                os.makedirs(FOLDER, exist_ok=True)
            file_path = f"{FOLDER}/{file_path}"
            with open(file_path, "wb") as ifile:
                for chunk in response.iter_content(chunk_size=1000000):
                    ifile.write(chunk)
            saved, _ = SavedImages.objects.get_or_create(
                image=image,
                subreddit=image.subreddit,
                reddit_id=image.reddit_id,
                link=image.link,
                downloaded_at=file_path,
            )
            print("Saved Image:", saved)
            return HttpResponse("YES")
        except Exception as e:
            print(e)
            print("couldn't save")
            return HttpResponse(e)

class SavedImagesView(ListView):
    model = SavedImages
    template_name = "gallery.html"
    context_object_name = "saved_images"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = SavedImages.objects.count()
        context["subs"] = SubReddit.objects.all()
        context["images"] = [image.image for image in SavedImages.objects.all().order_by("-pk")]
        return context


class FolderView(ListView):
    model = SubReddit
    template_name = "folders.html"
    context_object_name = "subs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = Image.objects.count()
        context["form"] = SubRedditForm()
        return context

    def get_queryset(self):
        return SubReddit.objects.select_related().all().order_by("sub_reddit")

    def post(self, request, *args, **kwargs):
        form = SubRedditForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/")
        else:
            print("Form is not valid:", form.errors)
            return redirect("/")


class MainSettingsView(CreateView):
    model = MainSettings
    template_name = "settings.html"
    form_class = SettingsForm

    def __init__(self, **kwargs):
        if not MainSettings.objects.exists():
            MainSettings.get_or_create_settings()
        self.object: MainSettings = MainSettings.get_or_create_settings()
        self.form_class = SettingsForm
        self.initial = self.object.get_initials()
        super().__init__(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return reverse("settings")  # Redirect to the settings page after saving


class FolderOptionsView(View):
    def post(self, request, *args, **kwargs):
        data = request.POST
        pk = data.get("pk", 0)
        if pk != 0:
            sub_reddit = SubReddit.objects.get(pk=pk)
            if "excluded" in data.keys():
                if sub_reddit.excluded:
                    sub_reddit.excluded = False
                else:
                    sub_reddit.excluded = True
                sub_reddit.save()
                main_settings = MainSettings.get_or_create_settings()
                if sub_reddit.sub_reddit not in main_settings.excluded_subs:
                    main_settings.exluded_subreddits += f"{sub_reddit.sub_reddit},"
                    main_settings.save()
            elif "delete" in data.keys():
                sub_reddit.delete()
                return redirect("folder_view")
            elif "sync" in data.keys():
                sync_singular(sub_reddit)
            return redirect("folder_view_detail", pk=pk)
        else:
            if "sync" in data.keys():
                sync_data()
            if "clear_ignored" in data.keys():
                ignored = IgnoredPosts.objects.all()
                ignored_count = IgnoredPosts.objects.count()
                ignored.delete()
                print("Cleared ignored posts:", ignored_count)
                return redirect("folder_view")
            elif "clean" in data.keys():
                posts: BaseManager[Post] = Post.objects.filter(
                    Q(image__isnull=True)
                    | Q(image__link__isnull=True)
                    | Q(image__link="")
                )
                posts.delete()
                # Multiple Objects of the same reddit_id can exist, so we need to delete them
                images_all = Image.objects.all().order_by("-date_added")
                print("Checking images, total:", images_all.count())
                loop_count = 0
                delete_images = 0
                bad_images = []
                for image in tqdm(images_all, total=float("inf")):
                    loop_count += 1
                    if not image.link or image.link == "":
                        bad_images.append(image)
                        image.post_ref.delete()
                        delete_images += 1
                        continue
                    if image.gallery is not None and image.gallery.image_set.count() <= 1:
                        remove_post = image.post_ref
                        bad_images.append(remove_post)
                        delete_images += image.gallery.image_set.count()
                        if remove_post:
                            remove_post.delete()
                        continue
                    if not check_if_good_image(image.link):
                        image_post = image.post_ref
                        bad_images.append(image_post)
                        image_post.delete()
                        delete_images += 1
                print(loop_count, "images checked", delete_images, "deleted")
                ic(bad_images)
        return redirect("folder_view")



class CleanView(View):
    """
    View to handle cleaning up the bad images and Posts.
    """

    def get(self, request, *args, **kwargs):
        return redirect("folder_view")
