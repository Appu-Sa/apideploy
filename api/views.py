from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import connection
from django.core.files.storage import default_storage
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views import View
import os
import uuid
from .models import User
from .serializers import UserSerializer
from .utils import upload_file_to_gcs, analyze_tennis_video_gcs, get_gcs_signed_url, delete_file_from_gcs, list_files_from_gcs_folder


@api_view(['GET'])
def home(request):
    """Home endpoint"""
    return Response({"message": "Welcome to Django API with Cloud SQL PostgreSQL!"})


@api_view(['GET'])
def health_check(request):
    """Health check endpoint to verify database connection"""
    try:
        # Try to query the database
        user_count = User.objects.count()
        
        # Check database type
        db_engine = settings.DATABASES['default']['ENGINE']
        is_postgresql = 'postgresql' in db_engine
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'user_count': user_count,
            'database_type': 'PostgreSQL' if is_postgresql else 'SQLite',
            'environment': 'production' if is_postgresql else 'development'
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def initialize_database(request):
    """Manual database initialization endpoint"""
    try:
        # Add sample data if no users exist
        if User.objects.count() == 0:
            sample_users = [
                User(name="Alice", age=30, city="New York"),
                User(name="Bob", age=25, city="San Francisco"),
                User(name="Charlie", age=35, city="Chicago")
            ]
            
            User.objects.bulk_create(sample_users)
            
            return Response({
                'status': 'success',
                'message': 'Database initialized and sample data added',
                'users_created': len(sample_users)
            })
        else:
            return Response({
                'status': 'info',
                'message': 'Database already has data',
                'user_count': User.objects.count()
            })
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': 'Database initialization failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
def users_view(request):
    """Get all users or create a new user"""
    if request.method == 'GET':
        try:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_user(request, user_id):
    """Get user by ID"""
    try:
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_data(request):
    """Legacy endpoint for compatibility"""
    db_engine = settings.DATABASES['default']['ENGINE']
    is_postgresql = 'postgresql' in db_engine
    
    data = {
        "name": "Alice",
        "age": 30,
        "city": "New York",
        "message": "This is sample data. Use /api/users for database operations.",
        "database_type": "PostgreSQL" if is_postgresql else "SQLite"
    }
    return Response(data)


@api_view(['GET'])
def debug_info(request):
    """Debug endpoint to check database configuration"""
    try:
        # Get all environment variables that contain 'DATABASE'
        env_vars = {k: v for k, v in os.environ.items() if 'DATABASE' in k}
        
        db_engine = settings.DATABASES['default']['ENGINE']
        is_postgresql = 'postgresql' in db_engine
        
        return Response({
            'database_type': 'PostgreSQL' if is_postgresql else 'SQLite',
            'is_cloud_sql': 'cloudsql' in str(settings.DATABASES['default']) if settings.DATABASES['default'] else False,
            'environment': 'production' if is_postgresql else 'development',
            'env_vars': env_vars,
            'all_env_count': len(os.environ)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class UploadImageView(View):
    """Upload image to GCS"""
    
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file part in the request'}, status=400)
            
            file = request.FILES['file']
            if not file.name:
                return JsonResponse({'error': 'No selected file'}, status=400)
            
            if not settings.GCS_BUCKET:
                return JsonResponse({'error': 'GCS_BUCKET not configured'}, status=500)
            
            # Generate secure filename
            filename = f"{uuid.uuid4()}_{file.name}"
            
            url = upload_file_to_gcs(
                file, 
                filename, 
                settings.GCS_BUCKET, 
                allowed_types=["image/jpeg", "image/png", "image/jpg"], 
                max_size_mb=10
            )
            
            return JsonResponse({
                'status': 'success', 
                'image_url': url, 
                'filename': filename
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def get_image_url(request, filename):
    """Get signed URL for image"""
    try:
        if not settings.GCS_BUCKET:
            return Response({'error': 'GCS_BUCKET not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        url = get_gcs_signed_url(filename, settings.GCS_BUCKET)
        return Response({'image_url': url})
        
    except FileNotFoundError:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class UploadVideoView(View):
    """Upload and analyze video"""
    
    def post(self, request):
        try:
            if 'video' not in request.FILES:
                return JsonResponse({'error': 'No video file provided'}, status=400)
            
            video = request.FILES['video']
            if not video.name:
                return JsonResponse({'error': 'No selected file'}, status=400)
            
            if not settings.GCS_BUCKET:
                return JsonResponse({'error': 'GCS_BUCKET not configured'}, status=500)
            
            # Generate secure filename
            filename = f"{uuid.uuid4()}_{video.name}"
            
            # Upload to GCS
            url = upload_file_to_gcs(
                video, 
                filename, 
                settings.GCS_BUCKET, 
                allowed_types=["video/mp4", "video/quicktime", "video/x-matroska"], 
                max_size_mb=200
            )
            
            gcs_uri = f"gs://{settings.GCS_BUCKET}/{filename}"
            
            # Analyze video for tennis
            tennis_labels, tennis_objects, shots = analyze_tennis_video_gcs(gcs_uri)
            
            return JsonResponse({
                'video_url': url,
                'tennis_labels': tennis_labels,
                'tennis_objects': tennis_objects,
                'shots': shots
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@api_view(['DELETE'])
def delete_file(request, filename):
    """Delete a file from GCS"""
    try:
        if not settings.GCS_BUCKET:
            return Response({'error': 'GCS_BUCKET not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Validate filename format
        if not filename or len(filename.strip()) == 0:
            return Response({'error': 'Filename cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        if filename.strip().startswith('{') or len(filename) > 500:
            return Response({'error': 'Invalid filename format'}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_file_from_gcs(filename, settings.GCS_BUCKET)
        
        return Response({
            'status': 'success',
            'message': f'File "{filename}" deleted successfully'
        })
        
    except FileNotFoundError:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': f'Configuration error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_files(request):
    """List files from a specific folder in GCS"""
    try:
        if not settings.GCS_BUCKET:
            return Response({'error': 'GCS_BUCKET not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get folder path from query parameters
        folder_path = request.GET.get('folder', '')  # Default to root folder
        max_results = int(request.GET.get('max_results', 100))  # Default max 100 files
        
        # Validate max_results
        if max_results <= 0 or max_results > 1000:
            return Response({'error': 'max_results must be between 1 and 1000'}, status=status.HTTP_400_BAD_REQUEST)
        
        files = list_files_from_gcs_folder(folder_path, settings.GCS_BUCKET, max_results)
        
        return Response({
            'status': 'success',
            'folder': folder_path or 'root',
            'file_count': len(files),
            'max_results': max_results,
            'files': files
        })
        
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': f'Configuration error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def debug_gcs_config(request):
    """Debug GCS configuration and credentials"""
    try:
        debug_info = {
            'gcs_bucket': getattr(settings, 'GCS_BUCKET', 'Not configured'),
            'credentials_env_var_set': bool(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')),
            'credentials_path': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set'),
        }
        
        # Check if credentials file exists
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path:
            # Try both forward and backslash paths
            paths_to_try = [creds_path, creds_path.replace('/', '\\'), creds_path.replace('\\', '/')]
            file_found = False
            for path in paths_to_try:
                if os.path.exists(path):
                    debug_info['credentials_file_exists'] = True
                    debug_info['credentials_file_size'] = os.path.getsize(path)
                    debug_info['actual_path_used'] = path
                    file_found = True
                    break
            
            if not file_found:
                debug_info['credentials_file_exists'] = False
                debug_info['credentials_file_size'] = 'File not found'
                debug_info['paths_tried'] = paths_to_try
        
        # Test basic GCS connection
        try:
            from google.cloud import storage
            client = storage.Client()
            debug_info['gcs_client_created'] = True
            
            # Try to access the bucket
            if settings.GCS_BUCKET:
                bucket = client.bucket(settings.GCS_BUCKET)
                debug_info['bucket_accessible'] = bucket.exists()
            else:
                debug_info['bucket_accessible'] = 'No bucket configured'
                
        except Exception as gcs_error:
            debug_info['gcs_client_created'] = False
            debug_info['gcs_error'] = str(gcs_error)
        
        return Response({
            'status': 'debug_info',
            'debug': debug_info
        })
        
    except Exception as e:
        return Response({'error': f'Debug failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
