from django.urls import path
from . import views
from .api import urlpatterns as api_urls

urlpatterns = [
    path("", views.FolderView.as_view(), name="folder_view"),
    path("<int:pk>/", views.FolderOnlyView.as_view(), name="folder_view_detail"),
    path(
        "<int:folder_id>/get-folder-form/",
        views.FolderFormAjaxView.as_view(),
        name="get_folder_form",
    ),
    path(
        "folder-settings/",
        views.FolderSettingsFormView.as_view(),
        name="folder_settings",
    ),
    path("gallery/", views.ImageListView.as_view(), name="gallery"),
    # Add more URL patterns as needed
    path("settings/", views.MainSettingsView.as_view(), name="settings"),
    path("options/", views.FolderOptionsView.as_view(), name="folder_options"),
    path("saved/", views.SavedImagesView.as_view(), name="saved_images"),
    path("image/<int:pk>/save/", views.ImageSaveView.as_view(), name="image_save"),
    path("bulk_subs/", views.BulkUploadSubreddits.as_view(), name="bulk_upload"),
    # path('image/<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    # path('upload/', views.ImageUploadView.as_view(), name='image_upload'),
    # path('<int:pk>/', views.ImageDetailView.as_view(), name='image_detail'),
    # path('search/', views.ImageSearchView.as_view(), name='image_search'),
    # path('tag/<str:tag>/', views.ImageTagView.as_view(), name='image_tag'),
    # path('category/<str:category>/', views.ImageCategoryView.as_view(), name='image_category'),
    # path('archive/', views.ImageArchiveView.as_view(), name='image_archive'),
    # path('about/', views.AboutView.as_view(), name='about'),
] + api_urls
