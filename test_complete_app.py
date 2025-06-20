#!/usr/bin/env python3
"""
Complete JEE Gurukul App Test Script
Tests all major components: database, API, question generation, frontend integration
"""

import os
import sys
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_environment_variables():
    """Test if all required environment variables are set"""
    print_header("Testing Environment Variables")
    
    required_vars = [
        'SECRET_KEY',
        'GOOGLE_API_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_REDIRECT_URI',
        'GOOGLE_CLOUD_PROJECT',
        'GCS_BUCKET_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print_success(f"{var} is set")
    
    if missing_vars:
        print_error(f"Missing environment variables: {', '.join(missing_vars)}")
        print_info("Please check ENVIRONMENT_SETUP.md for setup instructions")
        return False
    
    return True

def test_database():
    """Test database connection and table creation"""
    print_header("Testing Database")
    
    try:
        from app import app, db, User, TestHistory, QuestionAttempt
        
        with app.app_context():
            # Create tables
            db.create_all()
            print_success("Database tables created successfully")
            
            # Test basic operations
            user_count = User.query.count()
            test_count = TestHistory.query.count()
            question_count = QuestionAttempt.query.count()
            
            print_info(f"Users in database: {user_count}")
            print_info(f"Tests in database: {test_count}")
            print_info(f"Questions in database: {question_count}")
            
            return True
            
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False

def test_gemini_api():
    """Test Gemini API connection"""
    print_header("Testing Gemini API")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print_error("GOOGLE_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Simple test prompt
        response = model.generate_content("Say 'Hello, JEE Gurukul!'")
        
        if response.text:
            print_success("Gemini API connection successful")
            print_info(f"Response: {response.text}")
            return True
        else:
            print_error("Empty response from Gemini API")
            return False
            
    except Exception as e:
        print_error(f"Gemini API test failed: {e}")
        return False

def test_google_cloud_storage():
    """Test Google Cloud Storage connection"""
    print_header("Testing Google Cloud Storage")
    
    try:
        from google.cloud import storage
        
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        if not bucket_name:
            print_error("GCS_BUCKET_NAME not found")
            return False
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        if bucket.exists():
            print_success(f"Bucket '{bucket_name}' exists")
            
            # Check for required files
            required_files = [
                'md_files/math.mmd',
                'md_files/physics.mmd', 
                'md_files/chemistry.mmd',
                'static/dist_topic.json'
            ]
            
            missing_files = []
            for file_path in required_files:
                blob = bucket.blob(file_path)
                if blob.exists():
                    print_success(f"✓ {file_path} exists")
                else:
                    missing_files.append(file_path)
                    print_warning(f"⚠ {file_path} not found")
            
            if missing_files:
                print_warning(f"Missing files: {', '.join(missing_files)}")
                print_info("Please upload these files to your GCS bucket")
            
            return True
        else:
            print_error(f"Bucket '{bucket_name}' does not exist")
            return False
            
    except Exception as e:
        print_error(f"Google Cloud Storage test failed: {e}")
        return False

def test_question_generation():
    """Test question generation functionality"""
    print_header("Testing Question Generation")
    
    try:
        from app import generate_question_simple
        
        # Test with mathematics
        question_data = generate_question_simple("mathematics", "algebra", "medium")
        
        if question_data:
            print_success("Question generation successful")
            print_info(f"Question: {question_data['question'][:100]}...")
            print_info(f"Options: {len(question_data['options'])} options")
            print_info(f"Correct answer: {question_data['correct_answer']}")
            return True
        else:
            print_error("Question generation returned None")
            return False
            
    except Exception as e:
        print_error(f"Question generation test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app startup"""
    print_header("Testing Flask App")
    
    try:
        from app import app
        
        # Test basic app configuration
        if app.config['SECRET_KEY']:
            print_success("Flask app configured with secret key")
        else:
            print_warning("Flask app secret key not set")
        
        # Test if app can be imported
        print_success("Flask app imports successfully")
        
        # Test basic route registration
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/login', '/signup', '/dashboard', '/api/generate-test']
        
        for route in expected_routes:
            if route in routes:
                print_success(f"✓ Route {route} registered")
            else:
                print_warning(f"⚠ Route {route} not found")
        
        return True
        
    except Exception as e:
        print_error(f"Flask app test failed: {e}")
        return False

def test_templates():
    """Test if all required templates exist"""
    print_header("Testing Templates")
    
    required_templates = [
        'base.html',
        'index.html',
        'login.html',
        'signup.html',
        'dashboard.html',
        'topics.html',
        'test.html',
        'test_results.html',
        'complete_profile.html'
    ]
    
    missing_templates = []
    for template in required_templates:
        template_path = f"templates/{template}"
        if os.path.exists(template_path):
            print_success(f"✓ {template} exists")
        else:
            missing_templates.append(template)
            print_error(f"❌ {template} missing")
    
    if missing_templates:
        print_error(f"Missing templates: {', '.join(missing_templates)}")
        return False
    
    return True

def test_dependencies():
    """Test if all required dependencies are installed"""
    print_header("Testing Dependencies")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'flask_migrate',
        'google.generativeai',
        'google.cloud.storage',
        'google_auth_oauthlib',
        'python_dotenv',
        'werkzeug'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"✓ {package} installed")
        except ImportError:
            missing_packages.append(package)
            print_error(f"❌ {package} not installed")
    
    if missing_packages:
        print_error(f"Missing packages: {', '.join(missing_packages)}")
        print_info("Run: pip install -r requirements.txt")
        return False
    
    return True

def run_complete_test():
    """Run all tests and provide summary"""
    print_header("JEE Gurukul Complete App Test")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Dependencies", test_dependencies),
        ("Database", test_database),
        ("Gemini API", test_gemini_api),
        ("Google Cloud Storage", test_google_cloud_storage),
        ("Question Generation", test_question_generation),
        ("Flask App", test_flask_app),
        ("Templates", test_templates)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    if passed == total:
        print_success("🎉 All tests passed! Your app is ready for deployment.")
        print_info("Next steps:")
        print_info("1. Set up your .env file with real credentials")
        print_info("2. Upload your MMD files to Google Cloud Storage")
        print_info("3. Deploy to your preferred platform")
        print_info("4. Update production environment variables")
    else:
        print_error("Some tests failed. Please fix the issues above before deploying.")
        print_info("Check ENVIRONMENT_SETUP.md for detailed setup instructions")
    
    return passed == total

if __name__ == "__main__":
    success = run_complete_test()
    sys.exit(0 if success else 1) 