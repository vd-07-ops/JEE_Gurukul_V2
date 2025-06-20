from google.cloud import storage
from google.oauth2 import service_account
import json
from typing import Dict, Any
import requests

# Initialize Google Cloud Storage client
credentials = service_account.Credentials.from_service_account_file(
    'google_cloud_service_account.json'
)
storage_client = storage.Client(credentials=credentials)

# Your bucket name
BUCKET_NAME = 'jee_gurukul'  # Your actual bucket name

# File paths in the bucket
STORAGE_PATHS = {
    'bucket_name': BUCKET_NAME,
    'questions': 'static/original_questions.json',
    'topic_dist': 'static/dist_topic.json',
    'mmd_files': {
        'mathematics': 'static/math.mmd',
        'physics': 'static/physics.mmd',
        'chemistry': 'static/chemistry.mmd'
    },
    'vector_db': {
        'base_path': 'vector_db/',
        'index_suffix': '_index.faiss',
        'documents_suffix': '_documents.pkl'
    }
}

class CloudStorage:
    def __init__(self):
        self.bucket = storage_client.bucket(BUCKET_NAME)

    def get_json_file(self, path: str) -> Dict[str, Any]:
        """Fetch and parse a JSON file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(path)
            content = blob.download_as_text()
            return json.loads(content)
        except Exception as e:
            print(f"Error fetching JSON from {path}: {e}")
            return {}

    def get_text_file(self, path: str) -> str:
        """Fetch a text file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(path)
            return blob.download_as_text()
        except Exception as e:
            print(f"Error fetching text from {path}: {e}")
            return ""

    def get_binary_file(self, path: str) -> bytes:
        """Fetch a binary file from Google Cloud Storage."""
        try:
            blob = self.bucket.blob(path)
            return blob.download_as_bytes()
        except Exception as e:
            print(f"Error fetching binary from {path}: {e}")
            return b""

    def upload_file(self, source_file: str, destination_blob_name: str):
        """Upload a file to Google Cloud Storage."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file)
            print(f"File {source_file} uploaded to {destination_blob_name}")
        except Exception as e:
            print(f"Error uploading {source_file}: {e}")

    def upload_file_from_memory(self, content: bytes, destination_blob_name: str):
        """Upload binary content to Google Cloud Storage."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_string(content)
            print(f"Content uploaded to {destination_blob_name}")
        except Exception as e:
            print(f"Error uploading to {destination_blob_name}: {e}")

    def get_questions(self) -> Dict[str, Any]:
        return self.get_json_file(STORAGE_PATHS['questions'])
    
    def get_topic_distribution(self) -> Dict[str, Any]:
        return self.get_json_file(STORAGE_PATHS['topic_dist'])
    
    def get_mmd_content(self, subject: str) -> str:
        return self.get_text_file(STORAGE_PATHS['mmd_files'][subject])

# Initialize cloud storage
cloud_storage = CloudStorage()