from django.urls import path
from . import views

urlpatterns = [
    # Home and health endpoints
    path('', views.home, name='home'),
    path('api/health/', views.health_check, name='health_check'),
    path('api/init-db/', views.initialize_database, name='initialize_database'),
    
    # User endpoints
    path('api/users/', views.users_view, name='users'),
    path('api/users/<int:user_id>/', views.get_user, name='get_user'),
    
    # Legacy endpoint
    path('api/data/', views.get_data, name='get_data'),
    path('api/debug/', views.debug_info, name='debug_info'),
    
    # File upload endpoints
    path('api/upload-image/', views.UploadImageView.as_view(), name='upload_image'),
    path('api/image-url/<str:filename>/', views.get_image_url, name='get_image_url'),
    path('api/upload-video/', views.UploadVideoView.as_view(), name='upload_video'),
    
    # File management endpoints
    path('api/files/delete/<str:filename>/', views.delete_file, name='delete_file'),
    path('api/files/list/', views.list_files, name='list_files'),
    path('api/debug/gcs/', views.debug_gcs_config, name='debug_gcs_config'),
]
