#!/usr/bin/env python3
"""
Test script to verify JEE Gurukul app integration
"""

import requests
import json
import time

def test_app_endpoints():
    """Test the main app endpoints"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing JEE Gurukul App Integration")
    print("=" * 50)
    
    # Test 1: Homepage
    print("\n1. Testing homepage...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Homepage loads successfully")
        else:
            print(f"❌ Homepage failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Homepage error: {e}")
    
    # Test 2: Login page
    print("\n2. Testing login page...")
    try:
        response = requests.get(f"{base_url}/login")
        if response.status_code == 200:
            print("✅ Login page loads successfully")
        else:
            print(f"❌ Login page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Login page error: {e}")
    
    # Test 3: Question generation
    print("\n3. Testing question generation...")
    try:
        response = requests.get(f"{base_url}/test-question-generation")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                question = data.get('question', {})
                print("✅ Question generation working!")
                print(f"   Subject: {question.get('subject')}")
                print(f"   Topic: {question.get('topic')}")
                print(f"   Question: {question.get('question', '')[:100]}...")
                print(f"   Options: {len(question.get('options', []))} options")
                print(f"   Correct Answer: {question.get('correct_answer')}")
            else:
                print(f"❌ Question generation failed: {data.get('message')}")
        else:
            print(f"❌ Question generation endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Question generation error: {e}")
    
    # Test 4: Signup page
    print("\n4. Testing signup page...")
    try:
        response = requests.get(f"{base_url}/signup")
        if response.status_code == 200:
            print("✅ Signup page loads successfully")
        else:
            print(f"❌ Signup page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Signup page error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Integration Test Complete!")
    print("\n📋 Next Steps:")
    print("1. Visit http://localhost:5000 to see the app")
    print("2. Test user registration and login")
    print("3. Test question generation for different subjects")
    print("4. Deploy to production when ready!")

if __name__ == "__main__":
    # Wait a moment for the app to start
    print("⏳ Waiting for app to start...")
    time.sleep(3)
    test_app_endpoints() 