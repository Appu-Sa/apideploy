from django.conf import settings
from google.cloud import storage
from google.cloud import videointelligence_v1 as vi
from datetime import timedelta
import os
import uuid


def upload_file_to_gcs(file_obj, filename, bucket_name, allowed_types=None, max_size_mb=10):
    """Upload file to Google Cloud Storage and return signed URL"""
    # Check for credentials
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        raise RuntimeError('GOOGLE_APPLICATION_CREDENTIALS environment variable not set or invalid')
    
    # Validate file type
    if allowed_types and file_obj.content_type not in allowed_types:
        raise ValueError(f'Invalid file type: {file_obj.content_type}')
    
    # Validate file size
    size_mb = file_obj.size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f'File too large: {size_mb:.2f} MB (max {max_size_mb} MB)')
    
    client = storage.Client()
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
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)
    
    if not blob.exists():
        raise FileNotFoundError('File not found')
    
    # Generate a signed URL valid for 1 hour
    url = blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")
    return url
