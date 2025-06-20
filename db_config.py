from pymongo import MongoClient
from typing import Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# MongoDB Atlas connection string (store in .env file)
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://your-connection-string')

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client['jee_gurukul']
        self.progress_collection = self.db['user_progress']
        self.performance_collection = self.db['user_performance']
        self.generated_questions_collection = self.db['generated_questions']

    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user progress data from MongoDB."""
        doc = self.progress_collection.find_one({'_id': user_id})
        return doc if doc else {}

    def save_user_progress(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save user progress data to MongoDB."""
        self.progress_collection.update_one(
            {'_id': user_id},
            {'$set': data},
            upsert=True
        )

    def get_user_performance(self, user_id: str) -> Dict[str, Any]:
        """Get user performance data from MongoDB."""
        doc = self.performance_collection.find_one({'_id': user_id})
        return doc if doc else {}

    def save_user_performance(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save user performance data to MongoDB."""
        self.performance_collection.update_one(
            {'_id': user_id},
            {'$set': data},
            upsert=True
        )

    def save_generated_questions(self, user_id: str, questions: list) -> None:
        """Save generated questions to MongoDB."""
        doc = {
            '_id': f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'user_id': user_id,
            'questions': questions,
            'timestamp': datetime.now()
        }
        self.generated_questions_collection.insert_one(doc)

# Initialize MongoDB connection
mongodb = MongoDB() 