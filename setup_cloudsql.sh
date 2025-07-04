#!/bin/bash

# Cloud SQL Setup Helper Script
# Run this script after creating your Cloud SQL instance

echo "=== Cloud SQL PostgreSQL Setup ==="
echo ""

echo "1. Make sure you have:"
echo "   - Created Cloud SQL PostgreSQL instance"
echo "   - Created database 'flask_app_db'"
echo "   - Enabled Cloud SQL Admin API"
echo ""

echo "2. Get your connection details:"
echo "   - Project ID: [YOUR_PROJECT_ID]"
echo "   - Region: [YOUR_REGION] (e.g., us-central1)"
echo "   - Instance Name: [YOUR_INSTANCE_NAME]"
echo "   - Database Name: flask_app_db"
echo "   - Username: postgres (or your custom user)"
echo "   - Password: [YOUR_PASSWORD]"
echo ""

echo "3. Your Cloud SQL connection string should be:"
echo "   postgresql://postgres:YOUR_PASSWORD@/flask_app_db?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME"
echo ""

echo "4. Set this as DATABASE_URL environment variable in Cloud Run:"
echo "   - Go to Cloud Run service"
echo "   - Edit & Deploy new revision"
echo "   - Variables & Secrets tab"
echo "   - Add environment variable:"
echo "     Name: DATABASE_URL"
echo "     Value: [your connection string from step 3]"
echo ""

echo "5. In Cloud Run Connections tab:"
echo "   - Add Cloud SQL connection"
echo "   - Select your Cloud SQL instance"
echo ""

echo "Example connection string:"
echo "postgresql://postgres:mypassword123@/flask_app_db?host=/cloudsql/my-project-123:us-central1:flask-api-db"
