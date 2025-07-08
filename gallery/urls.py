from django.urls import path
from . import views


urlpatterns = [
    path('', views.ImageListView.as_view(), name='gallery'),
    # Add more URL patterns as needed
    # path('image/<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    # path('upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('<int:pk>/save/', views.ImageSaveView.as_view(), name='image_save'),
    # path('search/', views.ImageSearchView.as_view(), name='image_search'),
    # path('tag/<str:tag>/', views.ImageTagView.as_view(), name='image_tag'),
    # path('category/<str:category>/', views.ImageCategoryView.as_view(), name='image_category'),
    # path('archive/', views.ImageArchiveView.as_view(), name='image_archive'),
    # path('about/', views.AboutView.as_view(), name='about'),
]

