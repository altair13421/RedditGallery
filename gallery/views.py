import os
import requests
import json

from collections import OrderedDict
from django.db import OperationalError, transaction
from django.db.models.manager import BaseManager
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db.models import Q

# Create your views here.
from django.views.generic import (
    ListView,
    View,
    DetailView,
    CreateView,
)
from django.http import (
    HttpResponse,
    JsonResponse,
)

from .forms import SettingsForm, SubRedditForm, SubSettingsForm

from .models import (
    Category,
    IgnoredPosts,
    Image,
    MainSettings,
    Post,
    SubReddit,
    SavedImages,
    Gallery,
)
from .utils import sync_data, sync_singular, check_if_good_image
from icecream import ic
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

workers = 10


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
    paginate_by = 2000  # Optional pagination

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = Image.objects.count()
        context["newest_image"] = Image.objects.order_by("-date_added").first()
        if (category := self.request.GET.get("category", "")) == "":
            context["subs"] = SubReddit.objects.filter(excluded=True)
        else:
            context["subs"] = SubReddit.objects.filter(categories=Category.objects.filter(name=category).first())
        context["categories"] = Category.get_all_categories()
        context["category_name"] = category
        return context

    def get_queryset(self):
        if self.request.GET.get("category", "") != "":
            category_name = self.request.GET.get("category", "")
            category = Category.objects.filter(name=category_name).first()
            if category:
                images = (
                    Image.objects.select_related()
                    .filter(subreddit__in=category.subs)
                    .order_by("-date_added")
                    .all()
                )
                return images
        return (
            Image.objects.select_related()
            .exclude(subreddit__excluded=True)
            .order_by("-date_added")
            .all()
        )

class ImageSaveView(View):
    def get(self, request, pk):
        image = Image.objects.get(pk=pk)
        headers = {
            "User-Agent": "PostmanRuntime/7.46.1",
            # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            # "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        try:
            response = requests.get(
                image.link, stream=True, headers=headers, timeout=20
            )
            response.raise_for_status()
            file_path = image.link.split("/")[-1]
            file_path = file_path.split("?")[0]
            if image.gallery is not None:
                file_path = f"{image.gallery.reddit_id}_{file_path}"
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
            print(f"couldn't save {image.link} | {image.subreddit}")
            return HttpResponse(e)


class SavedImagesView(ListView):
    model = SavedImages
    template_name = "gallery.html"
    context_object_name = "saved_images"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = SavedImages.objects.count()
        context["subs"] = SubReddit.objects.all()
        context["images"] = [
            image.image for image in SavedImages.objects.all().order_by("-pk")
        ]
        return context


class FolderView(ListView):
    model = SubReddit
    template_name = "folders.html"
    context_object_name = "subs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_images"] = Image.objects.count()
        context["form"] = SubRedditForm()
        context["categories"] = Category.objects.all()
        context["no_category_subs"] = SubReddit.objects.filter(categories__isnull=True)
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

    def get_success_url(self):
        return reverse("settings")  # Redirect to the settings page after saving


class FolderOptionsView(View):
    def post(self, request, *args, **kwargs):
        data = request.POST
        pk = data.get("pk", 0)
        if pk != 0:
            sub_reddit = SubReddit.objects.get(pk=pk)
            if "excluded" in data.keys():
                main_settings = MainSettings.get_or_create_settings()
                if sub_reddit.excluded:
                    sub_reddit.excluded = False
                    main_settings.excluded_subreddits = (
                        main_settings.excluded_subreddits.replace(
                            f"{sub_reddit.sub_reddit},", ""
                        )
                    )
                    main_settings.save()
                else:
                    sub_reddit.excluded = True
                    if sub_reddit.sub_reddit not in main_settings.excluded_subs:
                        main_settings.excluded_subreddits += f"{sub_reddit.sub_reddit},"
                        main_settings.save()
                sub_reddit.save()

            elif "delete" in data.keys():
                sub_reddit.delete()
                return redirect("folder_view")
            elif "clean" in data.keys():
                posts = Post.objects.filter(subreddit=sub_reddit).delete()
                images = Image.objects.filter(subreddit=sub_reddit).delete()
                gallerys = Gallery.objects.filter(subreddit=sub_reddit).delete()
                print(
                    f"Deleted {posts[0]} posts, {images[0]} images, {gallerys[0]} gallerys"
                )
            elif "sync" in data.keys():
                if (category := data.get("category", "")) != "":
                    subs = SubReddit.objects.filter(categories=Category.objects.filter(name=category).first())
                    print("sub_category:", category, "subs:", subs.count(), "names: ", [sub.sub_reddit for sub in subs])
                    for sub in subs:
                        print("Syncing Subreddit:", sub.sub_reddit)
                        sync_singular(sub)
                sync_singular(sub_reddit)
            return redirect("folder_view_detail", pk=pk)
        else:
            if "sync" in data.keys():
                if (category := data.get("category", "")) != "":
                    subs = SubReddit.objects.filter(categories=Category.objects.filter(name=category).first())
                    print("sub_category:", category, "subs:", subs.count(), "names: ", [sub.sub_reddit for sub in subs])
                    for sub in subs:
                        print("Syncing Subreddit:", sub.sub_reddit)
                        sync_singular(sub)
                sync_data()
            if "delete" in data.keys():
                print("deleting posts")
                i = 0
                for post_ in Post.objects.all().order_by("-date_added")[:1000]:
                    i += 1
                    if i % 50 == 0:
                        print("Deleted:", i, "/1000", post_)
                    post_.delete()
                return redirect("folder_view")
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
                # Imgur Images, if Any, Cause They Always 404
                imgur_images = Image.objects.filter(link__contains="imgur")
                imgur_images_count = imgur_images.count()
                imgur_images.delete()
                print("Deleted Imgur images:", imgur_images_count)
                # Multiple Objects of the same reddit_id can exist, so we need to delete them
                offset = 0
                images_all = Image.objects.all().order_by("-date_added")[offset:]
                image_count = images_all.count() - offset
                print("Checking images, total:", image_count - offset)
                count = 0

                # galleries = Gallery.objects.filter(id__in=[gallery.id for gallery in Gallery.objects.all() if gallery.image_set.count() == 2])
                # post_ref = Post.objects.filter(gallery__in=galleries)
                # post_ref.delete()
                # return redirect("folder_view")
                def clean_images(image: Image):
                    nonlocal count
                    count += 1
                    if count % 50 == 0:
                        print(count, "/", image_count)
                    k = 0
                    while k < 3:
                        try:
                            if not image.link or image.link == "":
                                ic(image)
                                image.post_ref.delete()
                                return
                            elif (
                                image.gallery is not None
                                and image.gallery.image_set.count() <= 1
                            ):
                                remove_post = image.post_ref
                                ic(
                                    "Gallery with 1 or less images, removing:",
                                    image.gallery,
                                    remove_post,
                                )
                                if remove_post:
                                    remove_post.delete()
                                return
                            elif not check_if_good_image(image.link):
                                image_post = image.post_ref
                                ic("Bad Image", image_post)
                                image_post.delete()
                                return
                            return
                        except OperationalError as E:
                            print("OperationalError, retrying:", E)
                            time.sleep(2)
                            k += 1
                        except Exception as e:
                            print("Error checking image:", e)
                            return

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [
                        executor.submit(clean_images, image) for image in images_all
                    ]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print("Error cleaning image:", e)
                # for image in images_all:
                # clean_images(image)
        return redirect("folder_view")


class CleanView(View):
    """
    View to handle cleaning up the bad images and Posts.
    """

    def get(self, request, *args, **kwargs):
        return redirect("folder_view")


class FolderFormAjaxView(View):
    """AJAX view to load form"""

    def get(self, request, folder_id):
        folder: SubReddit = get_object_or_404(SubReddit, pk=folder_id)

        # Pre-populate form with folder data
        initial_data = {
            "folder_id": folder.id,
            "sub_display_name": folder.sub_reddit,
            "excluded": folder.excluded,
            "sub": folder,
            "categories": folder.categories.all(),
        }

        form = SubSettingsForm(initial=initial_data)

        return render(request, "folder_settings.html", {"form": form, "folder": folder})


class FolderSettingsFormView(View):
    """Handle form submission"""

    def post(self, request):
        form = SubSettingsForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    folder_id = form.cleaned_data["folder_id"]
                    folder: SubReddit = get_object_or_404(SubReddit, pk=folder_id)
                    # Get selected categories
                    selected_categories = form.cleaned_data["categories"]

                    if selected_categories.count() != 0:
                        folder.categories.set(selected_categories)
                        folder.save()

                    # Handle new category creation
                    new_category_name = form.cleaned_data["new_category"]
                    if new_category_name:
                        new_category, created = Category.objects.get_or_create(
                            name=new_category_name.strip(),
                        )
                        folder.categories.add(new_category.id)
                        folder.save()

                    # Update folder with form data
                    folder.excluded = form.cleaned_data["excluded"]
                    main_settings = MainSettings.get_or_create_settings()
                    if folder.excluded:
                        if folder.sub_reddit not in main_settings.excluded_subs:
                            main_settings.excluded_subreddits += f"{folder.sub_reddit},"
                            main_settings.save()
                    else:
                        main_settings.excluded_subreddits = (
                            main_settings.excluded_subreddits.replace(
                                f"{folder.sub_reddit},", ""
                            )
                        )
                        main_settings.save()
                    folder.save()


                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {"success": True, "message": "Settings saved successfully!"}
                        )
                    return redirect("some_success_url")

            except Exception as e:
                print("Exception", e)
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "errors": f"Error saving settings: {str(e)}"}
                    )

        # Form is invalid
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})

        return JsonResponse({"success": False, "errors": "Invalid request"})


class CategoryCreateView(CreateView):
    model = Category

class BulkUploadSubreddits(View):

    def _handle_subs_only(self, subs_list):
        for sub_name in subs_list:
            sub_name = sub_name.strip()
            sub_form = SubRedditForm({"sub_reddit": sub_name})
            if sub_form.is_valid():
                try:
                    sub_form.save()
                    print("Added Subreddit:", sub_name)
                except Exception as e:
                    print("Error saving subreddit:", sub_name, e)
                    continue
            else:
                print("Invalid Subreddit Form for:", sub_name, sub_form.errors)

    def _handle_subs_with_categories(self, subs_dict):
        for sub_name, categories in subs_dict.items():
            sub_name = sub_name.strip()
            sub_form = SubRedditForm({"sub_reddit": sub_name})
            if sub_form.is_valid():
                try:
                    sub_instance = sub_form.save()
                    print("Added Subreddit:", sub_name)
                    for category_name in categories:
                        category_name = category_name.strip()
                        category, created = Category.objects.get_or_create(name=category_name)
                        sub_instance.categories.add(category)
                    sub_instance.save()
                except Exception as e:
                    print("Error saving subreddit:", sub_name, e)
                    continue
            else:
                print("Invalid Subreddit Form for:", sub_name, sub_form.errors)

    def _handle_export_subs(self):
        subs = SubReddit.objects.all()
        export_data = OrderedDict({"subs": {}})
        export_file_list = "subreddits_export.json"
        with open(export_file_list, "w") as ef:
            json.dump(
                {"subs": [sub.sub_reddit for sub in subs]}, ef, indent=4
            )
        for sub in subs:
            export_data["subs"][sub.sub_reddit] = [cat.name for cat in sub.categories.all()]
        export_file_category = "subreddits_category_export.json"
        with open(export_file_category, "w") as ef:
            json.dump(export_data, ef, indent=4)

    def post(self, request, *args, **kwargs):
        try:
            export = request.POST.get("export", "")

            if export == "Export":
                self._handle_export_subs()
                return redirect("folder_view")
            json_data = request.POST.get("json_data", "")

            data = json.loads(json_data)
            subs = data.get("subs", [])
            if isinstance(subs[0], dict):
                self._handle_subs_with_categories(subs)
            else:
                self._handle_subs_only(subs)
            return redirect("folder_view")
        except Exception as E:
            return HttpResponse(f"{E},Invalid JSON Data")

    def get(self, request, *args, **kwargs):
        # Renders the upload form
        return render(request, 'upload_subreddits.html')


