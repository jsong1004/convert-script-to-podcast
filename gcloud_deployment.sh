gcloud builds submit --config cloudbuild.yaml .

gcloud run services update voice-app --region us-central1 --update-env-vars GOOGLE_MODEL=gemini-2.5-flash-preview-05-20
