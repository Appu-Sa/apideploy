# GCS File Management API Documentation

## Overview
The Django API now includes endpoints for managing files in Google Cloud Storage (GCS). You can delete files and list files from specific folders.

## New Endpoints

### 1. Delete File from GCS

**Endpoint:** `DELETE /api/files/delete/<filename>/`

**Description:** Deletes a specific file from the GCS bucket.

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/files/delete/my-file.jpg"
```

**Response (Success):**
```json
{
    "status": "success",
    "message": "File \"my-file.jpg\" deleted successfully"
}
```

**Response (File Not Found):**
```json
{
    "error": "File not found"
}
```

---

### 2. List Files from GCS Folder

**Endpoint:** `GET /api/files/list/`

**Description:** Lists files from a specific folder in the GCS bucket.

**Query Parameters:**
- `folder` (optional): The folder path to list files from. Default is root folder.
- `max_results` (optional): Maximum number of files to return. Default is 100.

**Examples:**

List files from root folder:
```bash
curl "http://localhost:8000/api/files/list/"
```

List files from a specific folder:
```bash
curl "http://localhost:8000/api/files/list/?folder=images"
```

List files with custom limit:
```bash
curl "http://localhost:8000/api/files/list/?folder=videos&max_results=50"
```

**Response:**
```json
{
    "status": "success",
    "folder": "images",
    "file_count": 3,
    "max_results": 100,
    "files": [
        {
            "name": "images/photo1.jpg",
            "filename": "photo1.jpg",
            "size": 1024000,
            "created": "2025-07-11T10:30:00Z",
            "updated": "2025-07-11T10:30:00Z",
            "content_type": "image/jpeg",
            "full_path": "images/photo1.jpg"
        },
        {
            "name": "images/photo2.png",
            "filename": "photo2.png",
            "size": 2048000,
            "created": "2025-07-11T11:15:00Z",
            "updated": "2025-07-11T11:15:00Z",
            "content_type": "image/png",
            "full_path": "images/photo2.png"
        }
    ]
}
```

## File Object Structure

Each file object in the response contains:
- `name`: Full path including folder
- `filename`: Just the filename without path
- `size`: File size in bytes
- `created`: ISO timestamp when file was created
- `updated`: ISO timestamp when file was last updated
- `content_type`: MIME type of the file
- `full_path`: Complete path in the bucket

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `404`: File/folder not found
- `500`: Server error (e.g., GCS configuration issues)

## Authentication & Security

- The API uses Google Cloud credentials configured via `GOOGLE_APPLICATION_CREDENTIALS`
- Files are accessed from the bucket specified in `GCS_BUCKET` environment variable
- No additional authentication is required beyond GCP service account credentials

## Production Usage

For production deployment on Cloud Run, ensure:
1. Google Cloud credentials are mounted as a secret
2. `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to the credentials file
3. `GCS_BUCKET` environment variable is set to your bucket name

## Example Use Cases

1. **Clean up old files:** Use the list endpoint to find old files, then delete them
2. **Folder management:** Organize files by listing specific folders
3. **Storage monitoring:** Check file counts and sizes in different folders
4. **File verification:** Confirm files exist before processing
