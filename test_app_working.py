import requests
import json

def test_app():
    """Test if the Flask app is working correctly"""
    try:
        # Test the generate-test endpoint
        response = requests.post('http://127.0.0.1:5000/api/generate-test', 
                               json={'subject': 'physics', 'topic': 'Modern Physics'})
        
        if response.status_code == 200:
            data = response.json()
            print("✅ App is working!")
            print(f"Generated {len(data.get('questions', []))} questions")
            
            # Show first question details
            if data.get('questions'):
                q = data['questions'][0]
                print(f"\nFirst Question:")
                print(f"Text: {q.get('question_text', 'N/A')[:100]}...")
                print(f"Options: {q.get('options', [])}")
                print(f"Correct Answer: {q.get('correct_answer', 'N/A')}")
                print(f"Difficulty: {q.get('difficulty', 'N/A')}")
            
            return True
        else:
            print(f"❌ App returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to app. Make sure it's running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Error testing app: {e}")
        return False

if __name__ == "__main__":
    test_app() 