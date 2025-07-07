from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, View
from .models import Image

class ImageListView(ListView):
    model = Image
    template_name = 'gallery.html'
    context_object_name = 'images'
    paginate_by = 12  # Optional pagination

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_images'] = Image.objects.count()
        context['newest_image'] = Image.objects.order_by('-date_added').first()
        return context

    def get_queryset(self):
        return Image.objects.select_related().order_by("-date_added").all()



class ImageSaveView(View): ...

class ImageDetailView(View): ...

