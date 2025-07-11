from django.conf import settings
from google.cloud import storage
from google.cloud import videointelligence_v1 as vi
from datetime import timedelta
import os
import uuid
import json
import tempfile


def _get_gcs_client():
    """Get Google Cloud Storage client with proper credential handling"""
    creds_env = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_env:
        raise RuntimeError('GOOGLE_APPLICATION_CREDENTIALS environment variable not set')
    
    # Check if it's JSON content (starts with '{') or a file path
    if creds_env.strip().startswith('{'):
        # It's JSON content - create a temporary file
        try:
            # Validate JSON
            credentials_data = json.loads(creds_env)
            
            # Create a temporary file for the credentials
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(credentials_data, temp_file)
                temp_file_path = temp_file.name
            
            # Set the environment variable to the temp file path
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file_path
            
            # Create the client
            client = storage.Client()
            
            # Clean up the temp file after client creation
            try:
                os.unlink(temp_file_path)
            except:
                pass  # Ignore cleanup errors
                
            return client
            
        except json.JSONDecodeError:
            raise RuntimeError('Invalid JSON content in GOOGLE_APPLICATION_CREDENTIALS')
    else:
        # It's a file path
        if not os.path.exists(creds_env):
            raise RuntimeError(f'Google Cloud credentials file not found: {creds_env}')
        
        return storage.Client()


def upload_file_to_gcs(file_obj, filename, bucket_name, allowed_types=None, max_size_mb=10):
    """Upload file to Google Cloud Storage and return signed URL"""
    # Validate file type
    if allowed_types and file_obj.content_type not in allowed_types:
        raise ValueError(f'Invalid file type: {file_obj.content_type}')
    
    # Validate file size
    size_mb = file_obj.size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f'File too large: {size_mb:.2f} MB (max {max_size_mb} MB)')
    
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
    
    # Generate a signed URL valid for 1 hour
    url = blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")
    return url


def analyze_tennis_video_gcs(gcs_uri):
    """Analyze tennis video using Google Video Intelligence API"""
    client = vi.VideoIntelligenceServiceClient()
    features = [vi.Feature.LABEL_DETECTION, vi.Feature.OBJECT_TRACKING, vi.Feature.SHOT_CHANGE_DETECTION]
    
    operation = client.annotate_video(request={
        "input_uri": gcs_uri,
        "features": features,
        "video_context": {
            "label_detection_config": {
                "label_detection_mode": vi.LabelDetectionMode.SHOT_AND_FRAME_MODE,
                "stationary_camera": True
            }
        }
    })
    
    result = operation.result(timeout=300)
    
    # Tennis-related labels
    tennis_labels = set()
    for label in result.annotation_results[0].segment_label_annotations:
        desc = label.entity.description.lower()
        if any(word in desc for word in ["tennis", "racket", "ball", "player", "court"]):
            tennis_labels.add(label.entity.description)
    
    # Tennis-related objects
    tennis_objects = set()
    for obj in result.annotation_results[0].object_annotations:
        desc = obj.entity.description.lower()
        if any(word in desc for word in ["tennis", "racket", "ball", "player"]):
            tennis_objects.add(obj.entity.description)
    
    # Shots
    shots = []
    for s in result.annotation_results[0].shot_annotations:
        start = s.start_time_offset.total_seconds()
        end = s.end_time_offset.total_seconds()
        shots.append((round(start, 2), round(end, 2)))
    
    return list(tennis_labels), list(tennis_objects), shots


def get_gcs_signed_url(filename, bucket_name):
    """Get signed URL for existing file in GCS"""
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)
    
    if not blob.exists():
        raise FileNotFoundError('File not found')
    
    # Generate a signed URL valid for 1 hour
    url = blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")
    return url


def delete_file_from_gcs(filename, bucket_name):
    """Delete a file from Google Cloud Storage"""
    try:
        # Validate filename - it should not contain JSON content
        if filename.strip().startswith('{') or len(filename) > 500:
            raise ValueError(f'Invalid filename provided: {filename[:100]}...')
        
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        if not blob.exists():
            raise FileNotFoundError(f'File "{filename}" not found in bucket "{bucket_name}"')
        
        blob.delete()
        return True
        
    except Exception as e:
        # Add more specific error information
        error_msg = str(e)
        if 'File' in error_msg and '{' in error_msg:
            raise ValueError(f'Invalid filename format detected. Expected a simple filename, got JSON-like content.')
        raise


def list_files_from_gcs_folder(folder_path, bucket_name, max_results=100):
    """List files from a specific folder in Google Cloud Storage"""
    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        
        # Ensure folder_path ends with / if it's not empty
        if folder_path and not folder_path.endswith('/'):
            folder_path += '/'
        
        # List blobs with prefix
        blobs = bucket.list_blobs(prefix=folder_path, max_results=max_results)
        
        files = []
        for blob in blobs:
            # Skip the folder itself (empty blob with name ending in /)
            if blob.name == folder_path:
                continue
                
            files.append({
                'name': blob.name,
                'filename': blob.name.split('/')[-1],  # Just the filename without path
                'size': blob.size,
                'created': blob.time_created.isoformat() if blob.time_created else None,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'content_type': blob.content_type,
                'full_path': blob.name
            })
        
        return files
        
    except Exception as e:
        # Add more specific error information
        error_msg = str(e)
        if 'File' in error_msg and '{' in error_msg:
            raise ValueError(f'Invalid configuration detected. Check your credentials setup.')
        raise
