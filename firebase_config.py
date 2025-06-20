import firebase_admin
from firebase_admin import credentials, firestore, storage
import requests
from typing import Dict, Any
import json

# Initialize Firebase Admin SDK
cred = credentials.Certificate('firebase_service_account.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-project-id.appspot.com'  # Replace with your bucket name
})

# Get Firestore client
db = firestore.client()

# Firebase Storage URLs (replace these with your actual URLs after uploading files)
STORAGE_URLS = {
    'questions': 'https://storage.googleapis.com/your-bucket/static/original_questions.json',
    'topic_dist': 'https://storage.googleapis.com/your-bucket/static/dist_topic.json',
    'mmd_files': {
        'mathematics': 'https://storage.googleapis.com/your-bucket/static/math.mmd',
        'physics': 'https://storage.googleapis.com/your-bucket/static/physics.mmd',
        'chemistry': 'https://storage.googleapis.com/your-bucket/static/chemistry.mmd'
    }
}

def fetch_json_file(url: str) -> Dict[str, Any]:
    """Fetch and parse a JSON file from Firebase Storage."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching JSON from {url}: {e}")
        return {}

def fetch_text_file(url: str) -> str:
    """Fetch a text file from Firebase Storage."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching text from {url}: {e}")
        return ""

class FirebaseStorage:
    @staticmethod
    def get_questions() -> Dict[str, Any]:
        return fetch_json_file(STORAGE_URLS['questions'])
    
    @staticmethod
    def get_topic_distribution() -> Dict[str, Any]:
        return fetch_json_file(STORAGE_URLS['topic_dist'])
    
    @staticmethod
    def get_mmd_content(subject: str) -> str:
        return fetch_text_file(STORAGE_URLS['mmd_files'][subject])

class FirebaseUserData:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.progress_ref = db.collection('user_progress').document(user_id)
        self.performance_ref = db.collection('user_performance').document(user_id)
    
    def get_progress(self) -> Dict[str, Any]:
        doc = self.progress_ref.get()
        return doc.to_dict() if doc.exists else {}
    
    def get_performance(self) -> Dict[str, Any]:
        doc = self.performance_ref.get()
        return doc.to_dict() if doc.exists else {}
    
    def save_progress(self, data: Dict[str, Any]) -> None:
        self.progress_ref.set(data)
    
    def save_performance(self, data: Dict[str, Any]) -> None:
        self.performance_ref.set(data) 