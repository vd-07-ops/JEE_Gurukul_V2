import json
import random
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import numpy as np
import re
import time
from cloud_config import cloud_storage
from db_config import mongodb

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini Flash model
model = genai.GenerativeModel('gemini-pro')

# Constants for question type distribution
MCQ_PROBABILITY = 0.8  # 80% MCQ questions
NUMERICAL_PROBABILITY = 0.2  # 20% Numerical questions

# Constants for mastery levels
MASTERY_LEVELS = {
    0: "Not Started",
    1: "Beginner",
    2: "Intermediate",
    3: "Advanced",
    4: "Master"
}

# Constants for spaced repetition intervals (in days)
SPACED_REPETITION_INTERVALS = {
    1: 1,    # Level 1: Review next day
    2: 3,    # Level 2: Review after 3 days
    3: 7,    # Level 3: Review after a week
    4: 14,   # Level 4: Review after two weeks
    5: 30    # Level 5: Review after a month
}

# Constants for performance thresholds
TIME_THRESHOLD = 300  # 5 minutes in seconds
ACCURACY_THRESHOLD = 0.6  # 60% accuracy threshold
CONCEPT_REINFORCEMENT_THRESHOLD = 0.4  # 40% accuracy triggers concept reinforcement

class UserProgress:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.progress_data = self._load_progress_data()
        self.performance_data = self._load_performance_data()

    def _initialize_topic_progress(self) -> Dict:
        """Initialize progress data for a new topic."""
        return {
            "mastery_level": 0,
            "last_review": None,
            "next_review": None,
            "correct_streak": 0,
            "total_attempts": 0,
            "correct_attempts": 0,
            "average_time": 0,
            "consecutive_correct": 0,
            "consecutive_incorrect": 0,
            "last_5_times": [],  # Store last 5 completion times
            "last_5_accuracy": []  # Store last 5 accuracy scores
        }

    def _initialize_performance_data(self) -> Dict:
        """Initialize performance tracking data."""
        return {
            "question_types": {
                "mcq": {
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "average_time": 0,
                    "last_5_times": [],
                    "last_5_accuracy": []
                },
                "numerical": {
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "average_time": 0,
                    "last_5_times": [],
                    "last_5_accuracy": []
                }
            },
            "topics": {
                "mathematics": {},
                "physics": {},
                "chemistry": {}
            },
            "concepts": {}  # Track concept mastery
        }

    def _load_progress_data(self) -> Dict:
        """Load user's progress data from MongoDB."""
        data = mongodb.get_user_progress(self.user_id)
        if not data:
            # Initialize new progress data structure
            return {
                "subjects": {
                    "mathematics": {},
                    "physics": {},
                    "chemistry": {}
                },
                "last_session": None,
                "streak_days": 0,
                "total_questions_attempted": 0,
                "total_correct_answers": 0
            }
        return data

    def _load_performance_data(self) -> Dict:
        """Load user's performance data from MongoDB."""
        data = mongodb.get_user_performance(self.user_id)
        if not data:
            return self._initialize_performance_data()
        return data

    def update_progress(self, subject: str, topic: str, is_correct: bool, time_taken: float):
        """Update user's progress after answering a question."""
        if topic not in self.progress_data["subjects"][subject]:
            self.progress_data["subjects"][subject][topic] = self._initialize_topic_progress()
        
        topic_data = self.progress_data["subjects"][subject][topic]
        
        # Update basic stats
        topic_data["total_attempts"] += 1
        if is_correct:
            topic_data["correct_attempts"] += 1
            topic_data["consecutive_correct"] += 1
            topic_data["consecutive_incorrect"] = 0
        else:
            topic_data["consecutive_correct"] = 0
            topic_data["consecutive_incorrect"] += 1
        
        # Update average time
        topic_data["average_time"] = (topic_data["average_time"] * (topic_data["total_attempts"] - 1) + 
                                    time_taken) / topic_data["total_attempts"]
        
        # Update mastery level based on performance
        self._update_mastery_level(topic_data)
        
        # Update next review date based on spaced repetition
        self._update_review_schedule(topic_data)
        
        # Update global stats
        self.progress_data["total_questions_attempted"] += 1
        if is_correct:
            self.progress_data["total_correct_answers"] += 1
        
        self._save_progress_data()

    def _update_mastery_level(self, topic_data: Dict):
        """Update mastery level based on performance metrics."""
        accuracy = topic_data["correct_attempts"] / topic_data["total_attempts"]
        current_level = topic_data["mastery_level"]
        
        # Level up conditions
        if current_level < 4:  # Can't go beyond level 4
            if (accuracy >= 0.8 and topic_data["consecutive_correct"] >= 5 and 
                topic_data["total_attempts"] >= 10):
                topic_data["mastery_level"] = min(4, current_level + 1)
            elif (accuracy < 0.6 and topic_data["consecutive_incorrect"] >= 3):
                topic_data["mastery_level"] = max(0, current_level - 1)

    def _update_review_schedule(self, topic_data: Dict):
        """Update next review date based on spaced repetition."""
        current_level = topic_data["mastery_level"]
        days_to_add = SPACED_REPETITION_INTERVALS.get(current_level + 1, 30)
        
        topic_data["last_review"] = datetime.now().isoformat()
        topic_data["next_review"] = (datetime.now() + timedelta(days=days_to_add)).isoformat()

    def get_topics_for_review(self) -> List[Tuple[str, str]]:
        """Get topics that are due for review."""
        topics_for_review = []
        current_time = datetime.now()
        
        for subject, topics in self.progress_data["subjects"].items():
            for topic, data in topics.items():
                if data["next_review"]:
                    next_review = datetime.fromisoformat(data["next_review"])
                    if next_review <= current_time:
                        topics_for_review.append((subject, topic))
        
        return topics_for_review

    def get_weak_topics(self, min_attempts: int = 5) -> List[Tuple[str, str]]:
        """Get topics where user is struggling."""
        weak_topics = []
        
        for subject, topics in self.progress_data["subjects"].items():
            for topic, data in topics.items():
                if data["total_attempts"] >= min_attempts:
                    accuracy = data["correct_attempts"] / data["total_attempts"]
                    if accuracy < 0.6 or data["mastery_level"] < 2:
                        weak_topics.append((subject, topic))
        
        return weak_topics

    def _save_progress_data(self):
        """Save user's progress data to MongoDB."""
        mongodb.save_user_progress(self.user_id, self.progress_data)

    def update_performance(self, subject: str, topic: str, question_type: str, 
                          is_correct: bool, time_taken: float, concepts: List[str]):
        """Update user's performance metrics."""
        # Update question type performance
        type_data = self.performance_data["question_types"][question_type]
        type_data["total_attempts"] += 1
        if is_correct:
            type_data["correct_attempts"] += 1
        
        # Update time tracking
        type_data["last_5_times"].append(time_taken)
        if len(type_data["last_5_times"]) > 5:
            type_data["last_5_times"].pop(0)
        type_data["average_time"] = sum(type_data["last_5_times"]) / len(type_data["last_5_times"])
        
        # Update accuracy tracking
        accuracy = type_data["correct_attempts"] / type_data["total_attempts"]
        type_data["last_5_accuracy"].append(accuracy)
        if len(type_data["last_5_accuracy"]) > 5:
            type_data["last_5_accuracy"].pop(0)
        
        # Update topic performance
        if topic not in self.performance_data["topics"][subject]:
            self.performance_data["topics"][subject][topic] = {
                "total_attempts": 0,
                "correct_attempts": 0,
                "average_time": 0,
                "last_5_times": [],
                "last_5_accuracy": []
            }
        
        topic_data = self.performance_data["topics"][subject][topic]
        topic_data["total_attempts"] += 1
        if is_correct:
            topic_data["correct_attempts"] += 1
        
        # Update topic time tracking
        topic_data["last_5_times"].append(time_taken)
        if len(topic_data["last_5_times"]) > 5:
            topic_data["last_5_times"].pop(0)
        topic_data["average_time"] = sum(topic_data["last_5_times"]) / len(topic_data["last_5_times"])
        
        # Update topic accuracy tracking
        topic_accuracy = topic_data["correct_attempts"] / topic_data["total_attempts"]
        topic_data["last_5_accuracy"].append(topic_accuracy)
        if len(topic_data["last_5_accuracy"]) > 5:
            topic_data["last_5_accuracy"].pop(0)
        
        # Update concept performance
        for concept in concepts:
            if concept not in self.performance_data["concepts"]:
                self.performance_data["concepts"][concept] = {
                    "total_attempts": 0,
                    "correct_attempts": 0,
                    "last_review": None
                }
            concept_data = self.performance_data["concepts"][concept]
            concept_data["total_attempts"] += 1
            if is_correct:
                concept_data["correct_attempts"] += 1
            concept_data["last_review"] = datetime.now().isoformat()
        
        self._save_performance_data()

    def get_weak_areas(self) -> Tuple[List[str], List[str], List[str]]:
        """Get user's weak topics, question types, and concepts."""
        weak_topics = []
        weak_types = []
        weak_concepts = []
        
        # Analyze question type performance
        for q_type, data in self.performance_data["question_types"].items():
            if data["total_attempts"] >= 5:
                accuracy = data["correct_attempts"] / data["total_attempts"]
                avg_time = data["average_time"]
                if accuracy < ACCURACY_THRESHOLD or avg_time > TIME_THRESHOLD:
                    weak_types.append(q_type)
        
        # Analyze topic performance
        for subject, topics in self.performance_data["topics"].items():
            for topic, data in topics.items():
                if data["total_attempts"] >= 5:
                    accuracy = data["correct_attempts"] / data["total_attempts"]
                    avg_time = data["average_time"]
                    if accuracy < ACCURACY_THRESHOLD or avg_time > TIME_THRESHOLD:
                        weak_topics.append(f"{subject}:{topic}")
        
        # Analyze concept performance
        for concept, data in self.performance_data["concepts"].items():
            if data["total_attempts"] >= 3:
                accuracy = data["correct_attempts"] / data["total_attempts"]
                if accuracy < CONCEPT_REINFORCEMENT_THRESHOLD:
                    weak_concepts.append(concept)
        
        return weak_topics, weak_types, weak_concepts

    def needs_concept_reinforcement(self, subject: str, topic: str) -> bool:
        """Check if user needs concept reinforcement for a topic."""
        if topic in self.performance_data["topics"][subject]:
            data = self.performance_data["topics"][subject][topic]
            if data["total_attempts"] >= 5:
                accuracy = data["correct_attempts"] / data["total_attempts"]
                return accuracy < CONCEPT_REINFORCEMENT_THRESHOLD
        return False

    def _save_performance_data(self):
        """Save user's performance data to MongoDB."""
        mongodb.save_user_performance(self.user_id, self.performance_data)

class QuestionDatabase:
    def __init__(self):
        self.questions = cloud_storage.get_questions()
        self.questions_by_topic = self._organize_by_topic()
        self.mmd_content = self._load_mmd_content()

    def _load_mmd_content(self) -> Dict[str, Dict[str, str]]:
        """Load content from MMD files from Cloud Storage."""
        mmd_content = {
            "mathematics": {},
            "physics": {},
            "chemistry": {}
        }
        
        for subject in mmd_content.keys():
            content = cloud_storage.get_mmd_content(subject)
            if content:
                mmd_content[subject] = self._parse_mmd_content(content)
            else:
                print(f"Note: MMD content for {subject} not found. Using questions only for context.")
        
        return mmd_content

    def _parse_mmd_content(self, content: str) -> Dict[str, str]:
        """Parse MMD content into a dictionary of topics and their content."""
        topics = {}
        current_topic = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_topic:
                    topics[current_topic] = '\n'.join(current_content)
                current_topic = line[3:].strip()
                current_content = []
            elif current_topic:
                current_content.append(line)
        
        if current_topic:
            topics[current_topic] = '\n'.join(current_content)
        
        return topics

    def _organize_by_topic(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Organize questions by subject and topic."""
        organized = {
            "mathematics": {},
            "physics": {},
            "chemistry": {}
        }
        
        for q in self.questions:
            subject = q['subject'].lower()
            topic = q['topic']
            if topic not in organized[subject]:
                organized[subject][topic] = []
            organized[subject][topic].append(q)
        
        return organized

    def get_questions_by_topic(self, subject: str, topic: str) -> List[Dict]:
        """Get all questions for a specific topic."""
        return self.questions_by_topic.get(subject.lower(), {}).get(topic, [])

    def get_mmd_content(self, subject: str, topic: str) -> Optional[str]:
        """Get MMD content for a specific topic."""
        return self.mmd_content.get(subject.lower(), {}).get(topic)

    def get_similar_questions(self, subject: str, topic: str, num_questions: int = 3) -> List[Dict]:
        """Get similar questions from the database for reference."""
        subject_questions = self.questions_by_topic[subject]
        # For now, randomly select questions. In a real implementation, 
        # we would use semantic similarity to find truly similar questions
        return random.sample(subject_questions, min(num_questions, len(subject_questions)))

    def get_topic_content(self, subject: str, topic: str) -> str:
        """Get MMD content for a specific topic."""
        return self.mmd_content[subject].get(topic, "")

    def get_concept_content(self, subject: str, topic: str) -> str:
        """Get MMD content for a specific topic, formatted for concept reinforcement."""
        content = self.mmd_content[subject].get(topic, "")
        if content:
            return f"""Here's a quick review of key concepts for {topic}:

{content}

Focus on understanding these concepts before attempting the question."""
        return ""

def load_topic_distribution() -> Dict:
    """Load topic distribution from Cloud Storage."""
    return cloud_storage.get_topic_distribution()

def select_topic_for_user(subject: str, topic_dist: Dict, weak_topics: List[str]) -> str:
    """Select a topic based on user's weak areas and topic distribution."""
    # Filter weak topics for the given subject
    subject_weak_topics = [t.split(':')[1] for t in weak_topics if t.startswith(f"{subject}:")]
    
    if subject_weak_topics:
        # 70% chance to select from weak topics
        if random.random() < 0.7:
            return random.choice(subject_weak_topics)
    
    # Fall back to weighted random selection from all topics
    topics = topic_dist[subject]
    weights = list(topics.values())
    return random.choices(list(topics.keys()), weights=weights)[0]

def select_question_type() -> str:
    """Select question type based on the 80-20 distribution."""
    return "mcq" if random.random() < MCQ_PROBABILITY else "numerical"

def generate_question_prompt(subject: str, topic: str, question_type: str, 
                           similar_questions: List[Dict], topic_content: str,
                           user_mastery_level: int, needs_reinforcement: bool) -> str:
    """Generate a prompt for the Gemini model using similar questions and MMD content as context."""
    similar_questions_text = "\n\n".join([
        f"Example Question {i+1}:\n{q['question']}\nAnswer: {q['gold']}"
        for i, q in enumerate(similar_questions)
    ])

    # Adjust difficulty based on mastery level
    difficulty = "basic" if user_mastery_level <= 1 else "intermediate" if user_mastery_level <= 2 else "advanced"
    
    prompt = f"""Generate a JEE-level {question_type} question for {subject} on the topic of {topic}.
    The question should be {difficulty} level difficulty based on the user's mastery level.
    
    Use the following example questions as reference for style and difficulty level:
    {similar_questions_text}
    """
    
    if needs_reinforcement and topic_content:
        prompt += f"\nIMPORTANT: The user is struggling with this topic. Include a brief concept review before the question:\n{topic_content}\n"
    elif topic_content:
        prompt += f"\nUse the following topic content as additional context:\n{topic_content}\n"
    
    prompt += f"""
    The response should be in the following JSON format:
    {{
        "subject": "{subject}",
        "topic": "{topic}",
        "question_type": "{question_type}",
        "difficulty": "{difficulty}",
        "question": "The question text",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "The correct option letter (A/B/C/D)",
        "solution": "Step-by-step solution explaining how to solve the question",
        "concepts_tested": ["List of key concepts tested in this question"]
    }}
    
    IMPORTANT: Output ONLY the JSON object above. Do not include any explanation, markdown, or extra text. The output must be valid JSON.
    """
    
    return prompt

def extract_json_from_text(text: str) -> dict:
    """Try to extract the first JSON object from a string."""
    try:
        # Find the first {...} block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"Error extracting JSON from text: {e}")
    return None

def dummy_question(subject, topic, question_type, difficulty):
    return {
        "subject": subject,
        "topic": topic,
        "question_type": question_type,
        "difficulty": difficulty,
        "question": f"[DUMMY] What is 2+2?",
        "options": ["1", "2", "3", "4"],
        "answer": "D",
        "solution": "2+2=4, so the answer is D.",
        "concepts_tested": ["Addition"]
    }

def generate_personalized_questions(user_id: str, num_questions: int = 5) -> List[Dict]:
    """Generate personalized questions for a user based on their progress and weak areas."""
    # Initialize user progress tracker and question database
    user_progress = UserProgress(user_id)
    question_db = QuestionDatabase()
    
    # Get weak areas
    weak_topics, weak_types, weak_concepts = user_progress.get_weak_areas()
    
    # Load topic distribution
    topic_dist = load_topic_distribution()
    
    # Generate questions
    generated_questions = []
    
    for _ in range(num_questions):
        # Select subject and topic based on weak areas
        if weak_topics:
            subject, topic = random.choice(weak_topics).split(':')
        else:
            subject = random.choice(['mathematics', 'physics', 'chemistry'])
            topic = select_topic_for_user(subject, topic_dist, [])
        
        # Select question type based on weak areas
        if weak_types:
            question_type = random.choice(weak_types)
        else:
            question_type = select_question_type()
        
        # Ensure topic is initialized in progress data
        if topic not in user_progress.progress_data["subjects"][subject]:
            user_progress.progress_data["subjects"][subject][topic] = user_progress._initialize_topic_progress()
        mastery_level = user_progress.progress_data["subjects"][subject][topic]["mastery_level"]
        
        # Check if concept reinforcement is needed
        needs_reinforcement = user_progress.needs_concept_reinforcement(subject, topic)
        
        # Get similar questions and topic content
        similar_questions = question_db.get_similar_questions(subject, topic)
        topic_content = question_db.get_concept_content(subject, topic) if needs_reinforcement else question_db.get_topic_content(subject, topic)
        
        print(f"Generating {question_type} question for {subject} - {topic} (Mastery Level: {mastery_level})")
        if needs_reinforcement:
            print(f"Adding concept reinforcement for {topic}")
        
        # Generate question with context
        prompt = generate_question_prompt(subject, topic, question_type, 
                                        similar_questions, topic_content, mastery_level,
                                        needs_reinforcement)
        
        # Robust Gemini API call with retries and JSON extraction
        max_attempts = 3
        question_data = None
        for attempt in range(1, max_attempts+1):
            try:
                response = model.generate_content(prompt)
                print(f"[Gemini raw response attempt {attempt}]:\n{response.text}\n---")
                try:
                    question_data = json.loads(response.text)
                    print(f"Successfully parsed JSON for {topic}")
                    break
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON for {topic} on attempt {attempt}. Trying to extract JSON...")
                    question_data = extract_json_from_text(response.text)
                    if question_data:
                        print(f"Successfully extracted JSON for {topic}")
                        break
            except Exception as e:
                print(f"Error from Gemini API for {topic} on attempt {attempt}: {e}")
            time.sleep(1)  # Wait before retry
        
        if not question_data:
            print(f"All attempts failed for {topic}. Using dummy question.")
            difficulty = "basic" if mastery_level <= 1 else "intermediate" if mastery_level <= 2 else "advanced"
            question_data = dummy_question(subject, topic, question_type, difficulty)
        
        generated_questions.append(question_data)
    
    return generated_questions

def main():
    # Test user ID
    user_id = "test_user_001"
    
    print("\n=== Testing JEE Question Generation ===")
    print("Generating 3 sample questions...\n")
    
    questions = generate_personalized_questions(user_id, num_questions=3)
    
    # Print generated questions in a readable format
    for i, q in enumerate(questions, 1):
        print(f"\nQuestion {i}:")
        print(f"Subject: {q['subject'].title()}")
        print(f"Topic: {q['topic']}")
        print(f"Type: {q['question_type']}")
        print(f"Difficulty: {q['difficulty']}")
        print("\nQuestion:")
        print(q['question'])
        print("\nOptions:")
        for opt in q['options']:
            print(f"- {opt}")
        print(f"\nCorrect Answer: {q['answer']}")
        print("\nSolution:")
        print(q['solution'])
        print("\nConcepts Tested:")
        for concept in q['concepts_tested']:
            print(f"- {concept}")
        print("\n" + "="*80)
    
    # Save generated questions to MongoDB
    mongodb.save_generated_questions(user_id, questions)
    print(f"\nGenerated questions have been saved to MongoDB")

if __name__ == "__main__":
    main() 