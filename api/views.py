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
from .logging_utils import api_logger


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
            
            api_logger.log_database_operation('SELECT', 'User', count=len(users))
            api_logger.log_custom(f"Retrieved {len(users)} users", level='INFO', user_count=len(users))
            
            return Response(serializer.data)
        except Exception as e:
            api_logger.log_custom(f"Error retrieving users: {str(e)}", level='ERROR', error_type=type(e).__name__)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    elif request.method == 'POST':
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                
                api_logger.log_database_operation('INSERT', 'User', count=1)
                api_logger.log_custom(f"Created new user: {user.name}", level='INFO', 
                                    user_id=user.id, user_name=user.name)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                api_logger.log_custom(f"Invalid user data: {serializer.errors}", level='WARNING', 
                                    validation_errors=serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            api_logger.log_custom(f"Error creating user: {str(e)}", level='ERROR', error_type=type(e).__name__)
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
        api_logger.log_custom(f"Attempting to delete file: {filename}", level='INFO', filename=filename)
        
        if not settings.GCS_BUCKET:
            api_logger.log_custom("GCS_BUCKET not configured", level='ERROR')
            return Response({'error': 'GCS_BUCKET not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Validate filename format
        if not filename or len(filename.strip()) == 0:
            api_logger.log_custom("Empty filename provided", level='WARNING', filename=filename)
            return Response({'error': 'Filename cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        if filename.strip().startswith('{') or len(filename) > 500:
            api_logger.log_custom("Invalid filename format", level='WARNING', filename=filename[:100])
            return Response({'error': 'Invalid filename format'}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_file_from_gcs(filename, settings.GCS_BUCKET)
        
        api_logger.log_gcs_operation('DELETE', settings.GCS_BUCKET, filename, success=True)
        
        return Response({
            'status': 'success',
            'message': f'File "{filename}" deleted successfully'
        })
        
    except FileNotFoundError:
        api_logger.log_custom(f"File not found for deletion: {filename}", level='WARNING', filename=filename)
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        api_logger.log_custom(f"Validation error deleting file: {str(e)}", level='WARNING', filename=filename)
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        api_logger.log_custom(f"Configuration error deleting file: {str(e)}", level='ERROR', filename=filename)
        return Response({'error': f'Configuration error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        api_logger.log_custom(f"Unexpected error deleting file: {str(e)}", level='ERROR', filename=filename, error_type=type(e).__name__)
        return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_files(request):
    """List files from a specific folder in GCS"""
    try:
        folder_path = request.GET.get('folder', '')
        max_results = int(request.GET.get('max_results', 100))
        
        api_logger.log_custom(f"Listing files from folder: {folder_path or 'root'}", level='INFO', 
                             folder=folder_path, max_results=max_results)
        
        if not settings.GCS_BUCKET:
            api_logger.log_custom("GCS_BUCKET not configured", level='ERROR')
            return Response({'error': 'GCS_BUCKET not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Validate max_results
        if max_results <= 0 or max_results > 1000:
            api_logger.log_custom(f"Invalid max_results: {max_results}", level='WARNING', max_results=max_results)
            return Response({'error': 'max_results must be between 1 and 1000'}, status=status.HTTP_400_BAD_REQUEST)
        
        files = list_files_from_gcs_folder(folder_path, settings.GCS_BUCKET, max_results)
        
        api_logger.log_gcs_operation('LIST', settings.GCS_BUCKET, folder_path, 
                                   file_count=len(files), success=True)
        
        return Response({
            'status': 'success',
            'folder': folder_path or 'root',
            'file_count': len(files),
            'max_results': max_results,
            'files': files
        })
        
    except ValueError as e:
        api_logger.log_custom(f"Validation error listing files: {str(e)}", level='WARNING', folder=folder_path)
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        api_logger.log_custom(f"Configuration error listing files: {str(e)}", level='ERROR', folder=folder_path)
        return Response({'error': f'Configuration error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        api_logger.log_custom(f"Unexpected error listing files: {str(e)}", level='ERROR', 
                             folder=folder_path, error_type=type(e).__name__)
        return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def debug_gcs_config(request):
    """Debug GCS configuration and credentials"""
    try:
        debug_info = {
            'gcs_bucket': getattr(settings, 'GCS_BUCKET', 'Not configured'),
            'credentials_env_var_set': bool(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')),
        }
        
        # Check credentials format
        creds_env = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')
        
        if creds_env == 'Not set':
            debug_info['credentials_type'] = 'Not set'
        elif creds_env.strip().startswith('{'):
            debug_info['credentials_type'] = 'JSON content'
            debug_info['credentials_length'] = len(creds_env)
            # Validate JSON
            try:
                import json
                json.loads(creds_env)
                debug_info['json_valid'] = True
            except json.JSONDecodeError:
                debug_info['json_valid'] = False
        else:
            debug_info['credentials_type'] = 'File path'
            debug_info['credentials_path'] = creds_env
            
            # Try both forward and backslash paths for file existence check
            paths_to_try = [creds_env, creds_env.replace('/', '\\'), creds_env.replace('\\', '/')]
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
            from .utils import _get_gcs_client
            client = _get_gcs_client()
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


@api_view(['POST'])
def test_logging(request):
    """Test endpoint to demonstrate custom logging functionality"""
    try:
        message = request.data.get('message', 'Test log message')
        level = request.data.get('level', 'INFO').upper()
        
        # Log with various levels and custom data
        api_logger.log_custom(
            f"Test log: {message}", 
            level=level,
            test_endpoint=True,
            user_message=message,
            timestamp_test=True
        )
        
        # Log some different types of operations
        api_logger.log_custom("Testing database log", level='INFO', operation_type='database_test')
        api_logger.log_custom("Testing GCS log", level='INFO', operation_type='gcs_test') 
        api_logger.log_custom("Testing error log", level='WARNING', operation_type='error_test')
        
        return Response({
            'status': 'success',
            'message': f'Logged message with level {level}',
            'logged_message': message,
            'note': 'Check Google Cloud Logging console to see the structured logs'
        })
        
    except Exception as e:
        api_logger.log_custom(f"Error in test logging endpoint: {str(e)}", level='ERROR', 
                             error_type=type(e).__name__)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
