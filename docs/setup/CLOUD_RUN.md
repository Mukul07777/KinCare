# Deploy KinCare to Google Cloud Run

One container serves the website and the API (see `Dockerfile` and `cloudrun.sh`).

```sh
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Secrets (never put keys in the image or the repo)
printf '%s' 'your-gmail-app-password' | gcloud secrets create smtp-password --data-file=-
printf '%s' 'your-gemini-key'         | gcloud secrets create gemini-key --data-file=-
python -c "import secrets;print(secrets.token_hex(32),end='')" | gcloud secrets create kincare-data-key --data-file=-
python -c "import secrets;print(secrets.token_hex(32),end='')" | gcloud secrets create otp-secret --data-file=-

gcloud run deploy kincare --source . --region asia-south1 --allow-unauthenticated \
  --memory 2Gi --cpu 1 --min-instances 1 --max-instances 1 --no-cpu-throttling \
  --set-env-vars SMTP_HOST=smtp.gmail.com,SMTP_PORT=587,SMTP_USER=you@gmail.com,EMAIL_FROM="KinCare <you@gmail.com>" \
  --set-secrets SMTP_PASSWORD=smtp-password:latest,GEMINI_API_KEY=gemini-key:latest,KINCARE_DATA_KEY=kincare-data-key:latest,OTP_SECRET=otp-secret:latest
```

Why these flags:
- `--no-cpu-throttling --min-instances 1`: email reminders run on a one-minute loop inside the service. With throttled
  CPU or zero instances, reminders stop between requests.
- `--max-instances 1`: the database is SQLite in the container. For lasting data, mount a Cloud Storage bucket
  (`--add-volume name=data,type=cloud-storage,bucket=YOUR_BUCKET --add-volume-mount volume=data,mount-path=/data`)
  and set `KINCARE_DB=/data/kincare.db`.
- `TZ=Asia/Kolkata` is set in the image, so 08:00 doses mean 08:00 in India.

Check it: open the service URL and go to `/circle`; `GET /api/circle/email/status` shows which email provider and
whether Gemini is configured.
