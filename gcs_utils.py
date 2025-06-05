import os
from google.cloud import storage

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "startup-consulting")

def upload_to_gcs(local_file_path, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    return blob.public_url

def generate_gcs_signed_url(blob_name, expiration=3600):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(expiration=expiration)
    return url 