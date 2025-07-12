"""
Custom logging utilities for Google Cloud Logging integration
"""
import logging
import os
import json
import tempfile
from typing import Dict, Any, Optional


class CloudLoggingHandler(logging.Handler):
    """Custom logging handler for Google Cloud Logging"""
    
    def __init__(self):
        super().__init__()
        self._client = None
        self._logger = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Cloud Logging client"""
        try:
            # Check if we're in a GCP environment or have credentials
            creds_env = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_env:
                # No credentials available, use console logging only
                return
            
            from google.cloud import logging as cloud_logging
            
            # Handle both JSON content and file path formats
            if creds_env.strip().startswith('{'):
                # It's JSON content - create a temporary file
                try:
                    credentials_data = json.loads(creds_env)
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(credentials_data, temp_file)
                        temp_file_path = temp_file.name
                    
                    # Temporarily set the environment variable
                    original_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file_path
                    
                    # Create the client
                    self._client = cloud_logging.Client()
                    
                    # Restore original environment variable
                    if original_creds:
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = original_creds
                    
                    # Clean up temp file
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                        
                except json.JSONDecodeError:
                    print("Warning: Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS")
                    return
            else:
                # It's a file path
                if os.path.exists(creds_env):
                    self._client = cloud_logging.Client()
                else:
                    print(f"Warning: Credentials file not found: {creds_env}")
                    return
            
            if self._client:
                # Setup Cloud Logging
                self._client.setup_logging()
                self._logger = self._client.logger('django-api')
                print("Google Cloud Logging initialized successfully")
                
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Logging: {e}")
            self._client = None
            self._logger = None
    
    def emit(self, record):
        """Emit a log record to Google Cloud Logging"""
        if not self._logger:
            # Fall back to console logging if Cloud Logging is not available
            return
        
        try:
            # Format the log message
            message = self.format(record)
            
            # Create structured log entry
            log_entry = {
                'message': message,
                'severity': record.levelname,
                'timestamp': record.created,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            }
            
            # Add request information if available
            if hasattr(record, 'request'):
                request = record.request
                log_entry.update({
                    'http_request': {
                        'requestMethod': getattr(request, 'method', ''),
                        'requestUrl': getattr(request, 'build_absolute_uri', lambda: '')(),
                        'userAgent': request.META.get('HTTP_USER_AGENT', ''),
                        'remoteIp': self._get_client_ip(request),
                    }
                })
            
            # Add extra fields from the record
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'message', 'request']:
                    log_entry[key] = str(value)
            
            # Send to Cloud Logging
            self._logger.log_struct(log_entry, severity=record.levelname)
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error sending log to Cloud Logging: {e}")
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or ''


class APILogger:
    """Convenient logger class for API operations"""
    
    def __init__(self, name: str = 'api'):
        self.logger = logging.getLogger(name)
    
    def log_request(self, request, endpoint: str, **kwargs):
        """Log API request"""
        extra = {
            'endpoint': endpoint,
            'method': request.method,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self._get_client_ip(request),
            'request': request,
            **kwargs
        }
        self.logger.info(f"API Request: {request.method} {endpoint}", extra=extra)
    
    def log_response(self, request, endpoint: str, status_code: int, response_time: float = None, **kwargs):
        """Log API response"""
        extra = {
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time_ms': round(response_time * 1000, 2) if response_time else None,
            'request': request,
            **kwargs
        }
        
        level = 'INFO'
        if status_code >= 400:
            level = 'WARNING'
        if status_code >= 500:
            level = 'ERROR'
            
        getattr(self.logger, level.lower())(
            f"API Response: {request.method} {endpoint} - {status_code}", 
            extra=extra
        )
    
    def log_error(self, request, endpoint: str, error: Exception, **kwargs):
        """Log API error"""
        extra = {
            'endpoint': endpoint,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'request': request,
            **kwargs
        }
        self.logger.error(f"API Error: {endpoint} - {error}", extra=extra, exc_info=True)
    
    def log_gcs_operation(self, operation: str, bucket: str, filename: str = None, **kwargs):
        """Log GCS operations"""
        extra = {
            'operation': operation,
            'bucket': bucket,
            'filename': filename,
            **kwargs
        }
        self.logger.info(f"GCS Operation: {operation} on {bucket}/{filename or 'folder'}", extra=extra)
    
    def log_database_operation(self, operation: str, model: str = None, count: int = None, **kwargs):
        """Log database operations"""
        extra = {
            'operation': operation,
            'model': model,
            'count': count,
            **kwargs
        }
        self.logger.info(f"DB Operation: {operation} on {model}", extra=extra)
    
    def log_custom(self, message: str, level: str = 'INFO', **kwargs):
        """Log custom message with extra fields"""
        getattr(self.logger, level.lower())(message, extra=kwargs)
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or ''


# Global logger instance
api_logger = APILogger('api')
