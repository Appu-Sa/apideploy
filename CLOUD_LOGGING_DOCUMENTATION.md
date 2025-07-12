# Google Cloud Logging Integration Documentation

## Overview
The Django API now includes comprehensive logging integration with Google Cloud Logging, providing structured logs that can be monitored and analyzed in the Google Cloud Console.

## Features

### 1. Automatic Request/Response Logging
- All API requests and responses are automatically logged
- Includes request method, path, status code, response time
- Request/response bodies for small payloads
- Client IP addresses and user agents
- Query parameters and important headers

### 2. Custom Application Logging
- Structured logging for business operations
- GCS operations (upload, delete, list)
- Database operations (CRUD)
- Error tracking with stack traces
- Custom events with structured data

### 3. Cloud Logging Integration
- Automatic export to Google Cloud Logging
- Structured log entries with metadata
- Searchable and filterable in Cloud Console
- Integration with Cloud Monitoring and Alerting

## Log Levels

- **INFO**: General operational information
- **WARNING**: Warning conditions (validation errors, missing files)
- **ERROR**: Error conditions (exceptions, system errors)
- **DEBUG**: Detailed diagnostic information (development only)

## Log Structure

Each log entry includes:
```json
{
    "message": "Human-readable message",
    "severity": "INFO|WARNING|ERROR",
    "timestamp": "2025-07-11T18:30:00Z",
    "module": "views",
    "function": "delete_file",
    "line": 125,
    "custom_field": "custom_value"
}
```

For HTTP requests, additional fields:
```json
{
    "http_request": {
        "requestMethod": "POST",
        "requestUrl": "https://api.example.com/api/files/list/",
        "userAgent": "Mozilla/5.0...",
        "remoteIp": "203.0.113.1"
    },
    "response_time_ms": 245.67,
    "status_code": 200
}
```

## Usage Examples

### 1. Automatic Logging (Middleware)
All API requests are automatically logged:
```bash
# This request will be automatically logged
curl "https://your-api.com/api/files/list/"
```

### 2. Custom Logging in Views
```python
from .logging_utils import api_logger

def my_view(request):
    # Log with custom data
    api_logger.log_custom(
        "Processing file upload", 
        level='INFO',
        filename="document.pdf",
        user_id=request.user.id,
        file_size=1024000
    )
    
    # Log GCS operations
    api_logger.log_gcs_operation(
        'UPLOAD', 
        'my-bucket', 
        'document.pdf',
        success=True
    )
    
    # Log database operations
    api_logger.log_database_operation(
        'INSERT', 
        'Document', 
        count=1
    )
```

### 3. Error Logging
```python
try:
    # Some operation
    pass
except Exception as e:
    api_logger.log_error(request, '/api/upload/', e, 
                        filename="document.pdf")
```

## Testing Logging

### Test Endpoint
Use the test endpoint to verify logging is working:

```bash
# Test basic logging
curl -X POST "https://your-api.com/api/test/logging/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from API", "level": "INFO"}'
```

### Check Logs in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Logging** > **Logs Explorer**
3. Filter by:
   - Resource: `Cloud Run Service` (for production)
   - Log name: `django-api`
   - Severity: `INFO`, `WARNING`, `ERROR`

### Sample Queries

Filter by custom fields:
```
jsonPayload.operation_type="gcs_test"
jsonPayload.filename="document.pdf"
jsonPayload.user_id="123"
```

Filter by HTTP requests:
```
httpRequest.requestMethod="POST"
httpRequest.status>=400
```

## Configuration

### Local Development
Logs are written to console and optionally to Cloud Logging if credentials are available.

### Production (Cloud Run)
Set these environment variables:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# OR (JSON content directly)
GOOGLE_APPLICATION_CREDENTIALS='{"type":"service_account",...}'
```

### Log Levels by Environment
- **Development**: All levels (DEBUG, INFO, WARNING, ERROR)
- **Production**: INFO, WARNING, ERROR only

## Monitoring and Alerting

### Set up Alerts
1. Go to **Monitoring** > **Alerting**
2. Create alert policies for:
   - Error rate > threshold
   - Response time > threshold
   - Specific error patterns

### Example Alert Conditions
```
# High error rate
count(severity="ERROR") > 10 over 5 minutes

# Slow responses
avg(jsonPayload.response_time_ms) > 1000 over 2 minutes

# Specific errors
jsonPayload.error_type="FileNotFoundError"
```

## Best Practices

### 1. Structured Logging
Always include relevant context:
```python
api_logger.log_custom(
    "File processing completed",
    level='INFO',
    filename=filename,
    processing_time_ms=processing_time,
    file_size=file_size,
    success=True
)
```

### 2. Sensitive Data
Never log sensitive information:
- Passwords
- API keys
- Personal data (follow GDPR/privacy requirements)
- Full request bodies with sensitive data

### 3. Performance
- Log entries are non-blocking
- Large payloads are truncated automatically
- Failed logging doesn't break the application

### 4. Error Context
Include enough context for debugging:
```python
api_logger.log_custom(
    f"Failed to process file: {str(e)}",
    level='ERROR',
    filename=filename,
    error_type=type(e).__name__,
    stack_trace=True
)
```

## Troubleshooting

### Logs Not Appearing in Cloud Console
1. Check credentials configuration
2. Verify service account has Cloud Logging Writer role
3. Check the debug endpoint: `/api/debug/gcs/`

### Performance Impact
- Minimal impact on response time
- Asynchronous logging to Cloud Logging
- Local console logging is synchronous (development only)

### Cost Considerations
- Cloud Logging has usage-based pricing
- Configure log retention policies
- Filter out noisy logs in production

## Integration with Other Services

### Cloud Monitoring
- Logs automatically appear in Cloud Monitoring
- Create dashboards from log data
- Set up SLIs/SLOs based on log metrics

### Error Reporting
- Structured error logs integrate with Error Reporting
- Automatic error grouping and notifications

### Cloud Run
- Integrated with Cloud Run request logs
- Correlation between application and infrastructure logs
