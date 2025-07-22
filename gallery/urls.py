from django.urls import path
from . import views


urlpatterns = [
    path('', views.FolderView.as_view(), name='folder_view'),
    path('<int:pk>/', views.FolderOnlyView.as_view(), name='folder_view_detail'),
    path('gallery/', views.ImageListView.as_view(), name='gallery'),
    # Add more URL patterns as needed
    path("settings/", views.MainSettingsView.as_view(), name="settings"),
    # path('image/<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    # path('upload/', views.ImageUploadView.as_view(), name='image_upload'),
    # path('<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('<int:pk>/save/', views.ImageSaveView.as_view(), name='image_save'),
    # path('search/', views.ImageSearchView.as_view(), name='image_search'),
    # path('tag/<str:tag>/', views.ImageTagView.as_view(), name='image_tag'),
    # path('category/<str:category>/', views.ImageCategoryView.as_view(), name='image_category'),
    # path('archive/', views.ImageArchiveView.as_view(), name='image_archive'),
    # path('about/', views.AboutView.as_view(), name='about'),
]

