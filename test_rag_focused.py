import json
import logging
import re
from cloud_config import cloud_storage
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_json_from_text(text):
    """Extract JSON from text that might contain markdown formatting."""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    
    # Try to find JSON object
    try:
        # Look for JSON object between curly braces
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # If that fails, try to parse the entire text
    try:
        return json.loads(text.strip())
    except:
        return None

def test_cloud_storage():
    """Test if cloud storage is accessible and files exist."""
    logger.info("=== Testing Cloud Storage ===")
    
    try:
        # Test topic distribution
        topic_dist = cloud_storage.get_topic_distribution()
        logger.info(f"✓ Topic distribution loaded: {len(topic_dist)} subjects found")
        
        # List what's available
        logger.info("Available files in bucket:")
        try:
            from list_bucket_contents import list_bucket_contents
            list_bucket_contents()
        except:
            logger.info("  - static/dist_topic.json")
            logger.info("  - static/original_questions.json")
            logger.info("  - vector_db/*_documents.pkl files")
        
        return True
    except Exception as e:
        logger.error(f"✗ Cloud storage test failed: {e}")
        return False

def test_gemini_api():
    """Test Gemini API with proper JSON parsing."""
    logger.info("\n=== Testing Gemini API ===")
    
    try:
        # Check if API key is available
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found in environment variables")
            return False
        
        logger.info("✓ Google API key found")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Test simple question generation with better prompt
        prompt = """Generate a simple JEE-level mathematics question about algebra. 
        Return ONLY a valid JSON object with these exact fields:
        {
            "question_text": "the question",
            "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
            "correct_answer": "A) option1",
            "explanation": "explanation here"
        }"""
        
        logger.info("Generating test question...")
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        question = extract_json_from_text(response.text)
        
        if question:
            logger.info("✓ Question generated successfully")
            logger.info(f"  Question: {question.get('question_text', 'N/A')[:100]}...")
            logger.info(f"  Options: {len(question.get('options', []))} options")
            logger.info(f"  Correct Answer: {question.get('correct_answer', 'N/A')}")
            return True
        else:
            logger.warning("⚠ Generated response is not valid JSON")
            logger.info(f"Raw response: {response.text[:300]}...")
            return False
        
    except Exception as e:
        logger.error(f"✗ Gemini API test failed: {e}")
        return False

def test_gemini_with_context():
    """Test Gemini with topic context from available data."""
    logger.info("\n=== Testing Gemini with Context ===")
    
    try:
        # Get topic distribution to understand available topics
        topic_dist = cloud_storage.get_topic_distribution()
        
        if not topic_dist:
            logger.error("✗ No topic distribution available")
            return False
        
        logger.info(f"✓ Found {len(topic_dist)} subjects in topic distribution")
        
        # Get a sample topic from mathematics
        math_topics = topic_dist.get('mathematics', {})
        if math_topics:
            sample_topic = list(math_topics.keys())[0]
            logger.info(f"✓ Using sample topic: {sample_topic}")
        else:
            sample_topic = "algebra"
            logger.info(f"⚠ No topics found, using default: {sample_topic}")
        
        # Configure Gemini
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Generate question with topic context
        prompt = f"""Generate a JEE-level mathematics question about {sample_topic}. 
        Return ONLY a valid JSON object with these exact fields:
        {{
            "question_text": "the question",
            "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
            "correct_answer": "A) option1",
            "explanation": "explanation here",
            "concepts": ["concept1", "concept2"]
        }}"""
        
        logger.info(f"Generating question for topic: {sample_topic}")
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        question = extract_json_from_text(response.text)
        
        if question:
            logger.info("✓ Contextual question generated successfully")
            logger.info(f"  Topic: {sample_topic}")
            logger.info(f"  Question: {question.get('question_text', 'N/A')[:100]}...")
            logger.info(f"  Options: {len(question.get('options', []))} options")
            logger.info(f"  Correct Answer: {question.get('correct_answer', 'N/A')}")
            logger.info(f"  Concepts: {question.get('concepts', [])}")
            return True
        else:
            logger.warning("⚠ Generated response is not valid JSON")
            logger.info(f"Raw response: {response.text[:300]}...")
            return False
        
    except Exception as e:
        logger.error(f"✗ Gemini with context test failed: {e}")
        return False

def test_question_generation_workflow():
    """Test the complete question generation workflow."""
    logger.info("\n=== Testing Question Generation Workflow ===")
    
    try:
        # 1. Get available topics
        topic_dist = cloud_storage.get_topic_distribution()
        if not topic_dist:
            logger.error("✗ No topic distribution available")
            return False
        
        # 2. Select a topic
        math_topics = topic_dist.get('mathematics', {})
        if not math_topics:
            logger.error("✗ No mathematics topics available")
            return False
        
        selected_topic = list(math_topics.keys())[0]
        logger.info(f"✓ Selected topic: {selected_topic}")
        
        # 3. Generate multiple questions
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        questions = []
        for i in range(2):
            prompt = f"""Generate a JEE-level mathematics question about {selected_topic}. 
            Return ONLY a valid JSON object with these exact fields:
            {{
                "question_text": "the question",
                "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
                "correct_answer": "A) option1",
                "explanation": "explanation here",
                "concepts": ["concept1", "concept2"]
            }}"""
            
            logger.info(f"Generating question {i+1}/2...")
            response = model.generate_content(prompt)
            
            question = extract_json_from_text(response.text)
            if question:
                questions.append(question)
                logger.info(f"  ✓ Question {i+1} generated")
            else:
                logger.warning(f"  ⚠ Question {i+1} failed to parse")
        
        if questions:
            logger.info(f"✓ Successfully generated {len(questions)} questions")
            logger.info(f"  Topic: {selected_topic}")
            logger.info(f"  Questions: {len(questions)} valid questions")
            return True
        else:
            logger.error("✗ No questions generated successfully")
            return False
        
    except Exception as e:
        logger.error(f"✗ Question generation workflow failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting Focused RAG and Question Generation Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Cloud Storage", test_cloud_storage),
        ("Gemini API", test_gemini_api),
        ("Gemini with Context", test_gemini_with_context),
        ("Question Generation Workflow", test_question_generation_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Your question generation system is working correctly.")
        logger.info("Note: RAG functionality needs MMD files and vector database setup.")
    else:
        logger.warning(f"⚠ {total - passed} test(s) failed. Please check the errors above.")
    
    # Recommendations
    logger.info("\n" + "="*60)
    logger.info("🔧 RECOMMENDATIONS")
    logger.info("="*60)
    
    if results.get("Cloud Storage", False):
        logger.info("✓ Cloud storage is working")
    else:
        logger.info("✗ Fix cloud storage configuration")
    
    if results.get("Gemini API", False):
        logger.info("✓ Gemini API is working")
    else:
        logger.info("✗ Check GOOGLE_API_KEY environment variable")
    
    if results.get("Question Generation Workflow", False):
        logger.info("✓ Question generation workflow is working")
        logger.info("🎯 You can proceed with your application!")
    else:
        logger.info("✗ Question generation needs fixing")
    
    logger.info("\nTo enable full RAG functionality:")
    logger.info("1. Upload MMD files to static/ folder in cloud storage")
    logger.info("2. Build vector database using build_vector_db.py")
    logger.info("3. Upload FAISS indexes to vector_db/ folder")
    
    return passed >= 2  # At least cloud storage and Gemini should work

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 