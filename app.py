from dotenv import load_dotenv
load_dotenv()

import os
import json
import logging
import threading
from datetime import datetime, date, UTC
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.genai as genai
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from flask_migrate import Migrate, upgrade
import re
from pydantic import BaseModel
from typing import List, Optional
import uuid
import concurrent.futures
import time
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ThreadTimeoutError
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Cloud Storage client
storage_client = storage.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

# Allow OAuth2 to work with HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configure Gemini
# def get_gemini_model():
#     api_key = os.getenv('GOOGLE_API_KEY')
#     if not api_key:
#         logger.error('GOOGLE_API_KEY not found in environment!')
#         return None
#     try:
#         genai.configure(api_key=api_key)
#         return genai.GenerativeModel('gemini-2.0-flash-001')
#     except Exception as e:
#         logger.error(f'Error configuring Gemini: {e}')
#         return None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
# Use DATABASE_URL from environment if available, otherwise fall back to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///jee_gurukul.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Google OAuth2 configuration
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv('GOOGLE_REDIRECT_URI')]
    }
}

# Global cache for original questions and generated questions
original_questions_cache = None
original_questions_set = set()
generated_questions_cache = {}
original_questions_lock = threading.Lock()

def load_original_questions():
    global original_questions_cache, original_questions_set
    with original_questions_lock:
        if original_questions_cache is not None:
            return
        try:
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            if not bucket_name:
                logger.error('GCS_BUCKET_NAME not set')
                return
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob('static/original_questions.json')
            if not blob.exists():
                logger.error('original_questions.json not found in GCS')
                return
            content = blob.download_as_text()
            original_questions_cache = json.loads(content)
            # Normalize all questions for fast comparison
            original_questions_set.clear()
            for q in original_questions_cache:
                norm = normalize_question_text(q.get('question', ''))
                if norm:
                    original_questions_set.add(norm)
            logger.info(f'Loaded {len(original_questions_set)} original questions from GCS')
        except Exception as e:
            logger.error(f'Error loading original_questions.json: {e}')

def normalize_question_text(text):
    return ' '.join(text.lower().strip().split())

def is_duplicate_question(question_text):
    norm = normalize_question_text(question_text)
    return norm in original_questions_set

def get_cached_question(subject, topic, difficulty):
    key = f'{subject.lower()}::{topic.lower()}::{difficulty.lower()}'
    return generated_questions_cache.get(key)

def cache_generated_question(subject, topic, difficulty, question_data):
    key = f'{subject.lower()}::{topic.lower()}::{difficulty.lower()}'
    generated_questions_cache[key] = question_data

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    mobile_number = db.Column(db.String(15))
    google_id = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    last_login = db.Column(db.DateTime)
    test_history = db.relationship('TestHistory', backref='user', lazy=True)

class TestHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer)
    time_taken = db.Column(db.Integer)  # in seconds
    completed_at = db.Column(db.DateTime, default=datetime.now(UTC))
    questions = db.relationship('QuestionAttempt', backref='test', lazy=True)

class QuestionAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test_history.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.Text)
    correct_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean)
    difficulty = db.Column(db.String(20), default='medium')
    hint_used = db.Column(db.Boolean, default=False)
    solution_viewed = db.Column(db.Boolean, default=False)
    concept_clarity_viewed = db.Column(db.Boolean, default=False)
    hint = db.Column(db.Text)
    concept = db.Column(db.Text)
    solution = db.Column(db.Text)  # New field for step-by-step solution

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Question Generation Functions
def get_mmd_content_for_topic(subject, topic):
    """Get relevant MMD content for a specific topic from the main MMD file."""
    try:
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable not set.")
        
        bucket = storage_client.bucket(bucket_name)
        
        # Map subject names to MMD file names
        subject_mapping = {
            'mathematics': 'math',
            'physics': 'physics', 
            'chemistry': 'chemistry',
            'math': 'math'  # Also handle 'math' directly
        }
        
        mmd_subject = subject_mapping.get(subject.lower(), subject.lower())
        mmd_file = f'md_files/{mmd_subject}.mmd'
        blob = bucket.blob(mmd_file)
        
        if not blob.exists():
            logger.error(f"MMD file {mmd_file} not found in GCS bucket {bucket_name}")
            return None
        
        mmd_content = blob.download_as_text()
        if not mmd_content:
            return None
        
        # Simple search for topic in the markdown content
        topic_lower = topic.lower()
        content_lower = mmd_content.lower()
        
        if topic_lower in content_lower:
            # Find the topic in the content
            start_idx = content_lower.find(topic_lower)
            # Get context around the topic (1000 chars before and 2000 chars after)
            start_context = max(0, start_idx - 1000)
            end_context = min(len(mmd_content), start_idx + 2000)
            relevant_content = mmd_content[start_context:end_context]
            return relevant_content
        else:
            # If topic not found, return first 2000 chars
            return mmd_content[:2000]
    except Exception as e:
        logger.error(f"Error getting MMD content for {subject}/{topic}: {e}")
        return None

def extract_json_from_text(text):
    try:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logger.error(f"Error extracting JSON: {e}")
    return None

# Pydantic models for structured output
class Option(BaseModel):
    id: str  # A, B, C, D
    text: str

class QuestionData(BaseModel):
    question_text: str
    options: List[Option]
    correct_answer: str
    solution: str
    difficulty: str = "medium"
    hint: Optional[str] = None
    concept: Optional[List[str]] = None  # Now a list of bullet points

def generate_question_rag_structured(subject, topic, difficulty="medium"):
    """Generate question using Google's structured output with Pydantic models, with timeout and robust fallback."""
    load_original_questions()
    mmd_content = get_mmd_content_for_topic(subject, topic)
    if not mmd_content:
        return fallback_question(subject, topic, difficulty, reason='no_mmd')
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error('GOOGLE_API_KEY not found in environment!')
        return fallback_question(subject, topic, difficulty, reason='no_api_key')
    prompt = f"""Generate a JEE-level {subject} question about {topic} with difficulty {difficulty}.
Content reference: {mmd_content[:1500]}
Requirements:
1. Create a challenging but fair question
2. Provide exactly 4 options (A, B, C, D)
3. Include a detailed step-by-step solution
4. Provide a helpful hint for the question
5. For the concept field, do NOT give a long explanation. Instead, return a concise, structured list of bullet points (as a JSON array of strings) with:
   - The main formula or law used (if any)
   - A 1-2 line summary of the key concept
   - A simple, short example (not a full solution)
   Example: ["Main formula: F = ma", "Newton's Second Law relates force, mass, and acceleration.", "Example: If m=2kg and a=3m/s^2, then F=6N."]
6. Ensure the correct answer is one of the options
7. Make the question relevant to the provided content
Return a structured JSON object with these fields: question_text, options, correct_answer, solution, hint, concept (as a list of bullet points), difficulty."""
    def call_gemini():
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": QuestionData,
                },
            )
            logger.info(f"[Gemini raw output]: {response.text}")
            return response
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    logger.info(f"[Gemini] Generating question for {subject}/{topic} ({difficulty})...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call_gemini)
        try:
            response = future.result(timeout=30)
            if response is None:
                logger.error("Gemini API returned None, using fallback.")
                return fallback_question(subject, topic, difficulty, reason='gemini_error')
            question_data: QuestionData = response.parsed
            question = {
                'id': str(uuid.uuid4()),
                'question_text': question_data.question_text,
                'options': [f"{opt.id}) {opt.text}" for opt in question_data.options],
                'correct_answer': question_data.correct_answer,
                'solution': question_data.solution,
                'difficulty': question_data.difficulty,
                'subject': subject,
                'topic': topic,
                'hint': getattr(question_data, 'hint', None),
                'concept': getattr(question_data, 'concept', None),
                'raw_gemini_output': response.text,
                'raw_gemini_output_step1': [response.text],
                'raw_gemini_output_step2': [response.text],
                'raw_gemini_output_step3': [response.text]
            }
            logger.info(f"[Gemini] ✓ Question generated successfully.")
            return question
        except concurrent.futures.TimeoutError:
            logger.error("Gemini API call timed out, using fallback.")
            return fallback_question(subject, topic, difficulty, reason='timeout')
        except Exception as e:
            logger.error(f"Error in structured question generation: {e}")
            return fallback_question(subject, topic, difficulty, reason=f'structured_error: {str(e)}')

# Update the main generation function to use structured output
def generate_question_rag(subject, topic, difficulty="medium"):
    """Main function - now uses structured output"""
    return generate_question_rag_structured(subject, topic, difficulty)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')
            else:
                email = request.form.get('email')
                password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            if user and user.password_hash and check_password_hash(user.password_hash, password):
                login_user(user)
                user.last_login = datetime.now(UTC)
                db.session.commit()
                logger.info(f"User {email} logged in successfully.")
                if request.is_json:
                    return jsonify({'user': {
                        'id': user.id,
                        'email': user.email,
                        'full_name': user.full_name,
                        'google_id': user.google_id
                    }})
                return redirect(url_for('dashboard'))
            logger.warning(f"Failed login attempt for {email}")
            if request.is_json:
                return jsonify({'error': 'Invalid email or password'}), 401
            flash('Invalid email or password')
        except Exception as e:
            logger.error(f"/login error: {e}")
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            flash('Internal server error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')
                full_name = data.get('full_name')
            else:
                email = request.form.get('email')
                password = request.form.get('password')
                full_name = request.form.get('full_name')
            if not email or not password:
                logger.warning("Signup missing email or password")
                if request.is_json:
                    return jsonify({'error': 'Email and password are required'}), 400
                flash('Email and password are required')
                return redirect(url_for('signup'))
            if User.query.filter_by(email=email).first():
                logger.warning(f"Signup failed: {email} already registered")
                if request.is_json:
                    return jsonify({'error': 'Email already registered'}), 409
                flash('Email already registered')
                return redirect(url_for('signup'))
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            logger.info(f"User {email} signed up successfully.")
            if request.is_json:
                return jsonify({'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'google_id': user.google_id
                }})
            return redirect(url_for('complete_profile'))
        except Exception as e:
            logger.error(f"/signup error: {e}")
            if request.is_json:
                return jsonify({'error': str(e)}), 500
            flash('Internal server error')
    return render_template('signup.html')

@app.route('/google-login')
def google_login():
    try:
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        logger.info(f"Google OAuth redirect: {authorization_url}")
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"/google-login error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/google-callback')
def google_callback():
    try:
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        session = flow.authorized_session()
        user_info = session.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
        user = User.query.filter_by(google_id=user_info['sub']).first()
        if not user:
            user = User(
                email=user_info['email'],
                google_id=user_info['sub'],
                full_name=user_info.get('name', '')
            )
            db.session.add(user)
            db.session.commit()
        login_user(user)
        logger.info(f"Google user {user.email} logged in.")
        response = make_response(redirect(url_for('dashboard')))
        return response
    except Exception as e:
        logger.error(f"/google-callback error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.date_of_birth = datetime.strptime(request.form.get('dob'), '%Y-%m-%d')
        current_user.mobile_number = request.form.get('mobile_number')
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('complete_profile.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

def get_topics_from_gcs(subject):
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME environment variable not set.")

    bucket = storage_client.bucket(bucket_name)
    blob_name = "static/dist_topic.json"
    blob = bucket.blob(blob_name)

    if not blob.exists():
        print(f"Error: {blob_name} not found in GCS bucket {bucket_name}")
        return {}

    try:
        content = blob.download_as_text()
        topics_data = json.loads(content)
        
        # Get the topics for the specific subject and extract only the topic names (keys)
        # Use subject.lower() to match the keys in dist_topic.json
        subject_topics_dict = topics_data.get(subject.lower(), {}) 
        return list(subject_topics_dict.keys())
    except Exception as e:
        print(f"Error reading or parsing {blob_name} from GCS: {e}")
        return {}

@app.route('/subject/<subject>')
@login_required
def subject_topics(subject):
    topics = get_topics_from_gcs(subject) # Now get_topics_from_gcs directly returns the list of topics
    if not topics:
        flash(f"No topics found for {subject.title()}. Please ensure dist_topic.json is correctly structured.")
        return redirect(url_for('dashboard'))
    
    return render_template('topics.html', subject=subject, topics=topics)

@app.route('/test/<subject>/<topic>')
@login_required
def start_test(subject, topic):
    return render_template('test.html', subject=subject, topic=topic)

# Add a global variable to store last raw outputs for debug endpoint
last_gemini_raw_outputs = {}

def fallback_question(subject, topic, difficulty, reason=''):
    """Fallback question with new structured format"""
    return {
        'id': str(uuid.uuid4()),
        'question_text': f"Sample question about {topic}",
        'options': ['A) Option A', 'B) Option B', 'C) Option C', 'D) Option D'],
        'correct_answer': 'A',
        'solution': 'This is a sample explanation.',
        'difficulty': difficulty,
        'subject': subject,
        'topic': topic,
        'is_fallback': True,
        'generation_status': reason,
        'raw_gemini_output': f"Fallback question - {reason}",
        'raw_gemini_output_step1': [f"Fallback - {reason}"],
        'raw_gemini_output_step2': [f"Fallback - {reason}"],
        'raw_gemini_output_step3': [f"Fallback - {reason}"]
    }

def generate_all_questions(subject, topic, difficulties, test_id):
    questions = []
    for i, difficulty in enumerate(difficulties):
        logger.info(f"Generating question {i+1}/5 for {subject}/{topic} with difficulty {difficulty}")
        question_data = generate_question_rag(subject, topic, difficulty)
        # Serialize concept list to JSON string if it's a list
        concept_value = question_data.get('concept', [])
        if isinstance(concept_value, list):
            concept_value = json.dumps(concept_value)
        qa = QuestionAttempt(
            test_id=test_id,
            question_text=question_data.get('question_text', question_data.get('question', '')),
            correct_answer=question_data.get('correct_answer', 'A'),
            difficulty=question_data.get('difficulty', difficulty),
            hint=question_data.get('hint', 'This is a helpful hint for the question. Consider the key concepts and formulas related to this topic.'),
            concept=concept_value,
            solution=question_data.get('solution', question_data.get('step_by_step_solution', 'No solution available.'))
        )
        db.session.add(qa)
        db.session.flush()  # Get ID
        question = {
            'id': qa.id,  # Use DB ID for frontend
            'question_text': qa.question_text,
            'options': question_data.get('options', []),
            'correct_answer': qa.correct_answer,
            'solution': qa.solution,
            'difficulty': qa.difficulty,
            'subject': subject,
            'topic': topic
        }
        questions.append(question)
    db.session.commit()  # Commit all questions before returning
    return questions

@app.route('/api/generate-test', methods=['POST'])
def generate_test():
    try:
        data = request.get_json()
        subject = data.get('subject')
        topic = data.get('topic')
        if not subject or not topic:
            return jsonify({'error': 'Subject and topic are required'}), 400
        difficulties = ['easy', 'medium', 'hard', 'medium', 'easy']
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        test = TestHistory(user_id=current_user.id, subject=subject, topic=topic)
        db.session.add(test)
        db.session.flush()  # Get test.id
        questions = generate_all_questions(subject, topic, difficulties, test.id)
        db.session.commit()  # Commit test and questions
        return jsonify({
            'test_id': test.id,
            'questions': questions,
            'subject': subject,
            'topic': topic,
            'total_questions': len(questions)
        })
    except Exception as e:
        logger.error(f"Error generating test: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-hint', methods=['POST'])
def get_hint():
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        if not question_id:
            return jsonify({'error': 'Question ID is required'}), 400
        qa = QuestionAttempt.query.get(question_id)
        if qa and qa.hint:
            return jsonify({'hint': qa.hint})
        return jsonify({'hint': 'This is a helpful hint for the question. Consider the key concepts and formulas related to this topic.'})
    except Exception as e:
        logger.error(f"Error getting hint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-solution', methods=['POST'])
def get_solution():
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        if not question_id:
            return jsonify({'error': 'Question ID is required'}), 400
        qa = QuestionAttempt.query.get(question_id)
        if qa:
            return jsonify({'solution': qa.solution})
        return jsonify({'solution': 'This is a detailed step-by-step solution to the question.'})
    except Exception as e:
        logger.error(f"Error getting solution: {e}")
        return jsonify({'error': str(e)}), 500

# Utility function to safely load concept as list
def get_concept_list(concept_field):
    if not concept_field:
        return []
    if isinstance(concept_field, list):
        return concept_field
    try:
        return json.loads(concept_field)
    except Exception:
        return [str(concept_field)]

@app.route('/api/get-concept-clarity', methods=['POST'])
def get_concept_clarity():
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        if not question_id:
            return jsonify({'error': 'Question ID is required'}), 400
        qa = QuestionAttempt.query.get(question_id)
        if qa and qa.concept:
            # Always return as a list
            return jsonify({'concept': get_concept_list(qa.concept)})
        return jsonify({'concept': ['This is a detailed explanation of the underlying concepts and principles.']})
    except Exception as e:
        logger.error(f"Error getting concept clarity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-test', methods=['POST'])
@login_required
def submit_test():
    test_id = request.json.get('test_id')
    answers = request.json.get('answers', [])
    time_taken = request.json.get('time_taken') # Get time_taken from frontend
    test = TestHistory.query.get_or_404(test_id)
    if test.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    score = 0
    for answer in answers:
        question = QuestionAttempt.query.get(answer['question_id'])
        if question and question.test_id == test_id:
            question.user_answer = answer['answer']
            if question.user_answer is None or question.user_answer == '':
                question.is_correct = None  # Unattempted
            else:
                question.is_correct = question.user_answer == question.correct_answer
            # JEE marking scheme
            if question.user_answer is None or question.user_answer == '':
                score += 0  # Unattempted
            elif question.is_correct:
                score += 4  # Correct
            else:
                score -= 1  # Incorrect
    test.score = score
    test.time_taken = time_taken  # Use the time_taken from frontend
    db.session.commit()
    return jsonify({
        'test_id': test_id,
        'score': score,
        'total_questions': len(answers)
    })

@app.route('/test-results/<int:test_id>')
@login_required
def test_results(test_id):
    test = TestHistory.query.get_or_404(test_id)
    if test.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    return render_template('test_results.html', test=test)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({'success': True})
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/test-question-generation')
def test_question_generation():
    """Test endpoint to verify Gemini output directly."""
    try:
        question_data = generate_question_rag("mathematics", "algebra", "medium")
        return jsonify({'status': 'success', 'question': question_data})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/debug-gemini-output', methods=['GET'])
@login_required
def debug_gemini_output():
    global last_gemini_raw_outputs
    return jsonify(last_gemini_raw_outputs)

@app.route('/api/me')
def api_me():
    if current_user.is_authenticated:
        return jsonify({'user': {
            'id': current_user.id,
            'email': current_user.email,
            'full_name': current_user.full_name,
            'google_id': current_user.google_id
        }})
    return jsonify({'user': None})

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

CORS(app, supports_credentials=True)

# === TEMPORARY: Migration route for Render free tier (REMOVE after use!) ===
@app.route('/run-migrations')
def run_migrations():
    upgrade()
    return "Migrations complete! (Remove this route after use)"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=5000) 