"""
Middleware for automatic API logging
"""
import time
import json
from django.utils.deprecation import MiddlewareMixin
from .logging_utils import api_logger


class APILoggingMiddleware(MiddlewareMixin):
    """Middleware to automatically log all API requests and responses"""
    
    def process_request(self, request):
        """Log incoming request"""
        request._start_time = time.time()
        
        # Skip logging for certain paths
        skip_paths = ['/static/', '/admin/', '/api/health/', '/favicon.ico']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Log the request
        extra_data = {}
        
        # Add request body for POST/PUT requests (limited size)
        if request.method in ['POST', 'PUT', 'PATCH'] and hasattr(request, 'body'):
            try:
                body = request.body.decode('utf-8')
                if len(body) < 1000:  # Only log small bodies
                    if request.content_type == 'application/json':
                        try:
                            extra_data['request_body'] = json.loads(body)
                        except json.JSONDecodeError:
                            extra_data['request_body'] = body
                    else:
                        extra_data['request_body'] = body
                else:
                    extra_data['request_body_size'] = len(body)
            except UnicodeDecodeError:
                extra_data['request_body'] = '[Binary data]'
        
        # Add query parameters
        if request.GET:
            extra_data['query_params'] = dict(request.GET)
        
        api_logger.log_request(request, request.path, **extra_data)
        return None
    
    def process_response(self, request, response):
        """Log outgoing response"""
        # Skip logging for certain paths
        skip_paths = ['/static/', '/admin/', '/api/health/', '/favicon.ico']
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        # Calculate response time
        response_time = None
        if hasattr(request, '_start_time'):
            response_time = time.time() - request._start_time
        
        # Prepare extra data
        extra_data = {}
        
        # Add response body for API endpoints (limited size)
        if (request.path.startswith('/api/') and 
            response.get('Content-Type', '').startswith('application/json')):
            try:
                content = response.content.decode('utf-8')
                if len(content) < 1000:  # Only log small responses
                    try:
                        extra_data['response_body'] = json.loads(content)
                    except json.JSONDecodeError:
                        extra_data['response_body'] = content
                else:
                    extra_data['response_body_size'] = len(content)
            except UnicodeDecodeError:
                extra_data['response_body'] = '[Binary data]'
        
        # Add response headers (selected ones)
        important_headers = ['Content-Type', 'Content-Length', 'Cache-Control']
        response_headers = {}
        for header in important_headers:
            if header in response:
                response_headers[header] = response[header]
        if response_headers:
            extra_data['response_headers'] = response_headers
        
        api_logger.log_response(
            request, 
            request.path, 
            response.status_code, 
            response_time,
            **extra_data
        )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions"""
        # Skip logging for certain paths
        skip_paths = ['/static/', '/admin/', '/favicon.ico']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        api_logger.log_error(request, request.path, exception)
        return None
