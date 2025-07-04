# Cloud Run Deployment Configuration

# 1. Build and Deploy Command:
# gcloud run deploy flask-api-postgresql \
#   --source . \
#   --platform managed \
#   --region us-central1 \
#   --allow-unauthenticated \
#   --set-env-vars="DATABASE_URL=postgresql://flask_user:YOUR_PASSWORD@/flask_app_db?host=/cloudsql/YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME" \
#   --add-cloudsql-instances="YOUR_PROJECT_ID:YOUR_REGION:YOUR_INSTANCE_NAME"

# 2. Example with your actual Cloud SQL connection:
# gcloud run deploy flask-api-postgresql \
#   --source . \
#   --platform managed \
#   --region us-central1 \
#   --allow-unauthenticated \
#   --set-env-vars="DATABASE_URL=postgresql://flask_user:Test@12345@/flask_app_db?host=/cloudsql/august-strata-462911-t2:asia-south1:api-56" \
#   --add-cloudsql-instances="august-strata-462911-t2:asia-south1:api-56"

# 3. Or deploy first without database connection to test:
# gcloud run deploy flask-api-postgresql \
#   --source . \
#   --platform managed \
#   --region us-central1 \
#   --allow-unauthenticated

# Then add the database connection via Cloud Console:
# - Go to Cloud Run service
# - Edit & Deploy new revision
# - Variables & Secrets tab: Add DATABASE_URL
# - Connections tab: Add Cloud SQL connection
