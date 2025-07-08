from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, View, DetailView
from django.http import HttpResponse

from .models import Image, SubReddit
import requests
from django.conf import settings

class FolderOnlyView(DetailView):
    model = SubReddit
    template_name = 'gallery.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subreddit: SubReddit = self.get_object()
        images = Image.objects.filter(subreddit=subreddit).select_related().order_by("-date_added")
        context['total_images'] = Image.objects.count()
        context['newest_image'] = Image.objects.order_by('-date_added').first()
        context['subs'] = SubReddit.objects.all()
        context["active_sub"] = subreddit.sub_reddit
        context["images"] = images
        return context

class ImageListView(ListView):
    model = Image
    template_name = 'gallery.html'
    context_object_name = 'images'
    # paginate_by = 12  # Optional pagination

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_images'] = Image.objects.count()
        context['newest_image'] = Image.objects.order_by('-date_added').first()
        context["subs"] = SubReddit.objects.all()
        return context

    def get_queryset(self):
        return Image.objects.select_related().order_by("-date_added").all()



class ImageSaveView(View):
    def get(self, request, pk):
        image = Image.objects.get(pk=pk)
        download_url = image.link
        try:
            response = requests.get(image.link, stream=True)
            response.raise_for_status()
            file_path = image.link.split("/")[-1]
            file_path = file_path.split("?")[0]
            FOLDER = settings.DOWNLOAD_PATH / image.subreddit.sub_reddit
            if not FOLDER.exists():
                FOLDER.mkdir(parents=True, exist_ok=True)
            file_path = FOLDER / file_path
            with open( file_path, 'wb') as ifile:
                for chunk in response.iter_content(chunk_size=1000000):
                    ifile.write(chunk)
            print("saved at ", file_path)
            return HttpResponse("YES")
        except Exception as e:
            print(e)
            print("couldn't save")
            ...

class FolderView(ListView):
    model = SubReddit
    template_name = 'folders.html'
    context_object_name = 'subs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_queryset(self):
        return SubReddit.objects.select_related().all()

