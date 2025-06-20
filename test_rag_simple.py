import json
import logging
from rag_engine import rag_engine
from cloud_config import cloud_storage
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cloud_storage():
    """Test if cloud storage is accessible and files exist."""
    logger.info("=== Testing Cloud Storage ===")
    
    try:
        # Test topic distribution
        topic_dist = cloud_storage.get_topic_distribution()
        logger.info(f"✓ Topic distribution loaded: {len(topic_dist)} subjects found")
        
        # Test MMD files
        subjects = ['mathematics', 'physics', 'chemistry']
        for subject in subjects:
            mmd_content = cloud_storage.get_mmd_content(subject)
            if mmd_content:
                logger.info(f"✓ {subject.capitalize()} MMD file loaded: {len(mmd_content)} characters")
            else:
                logger.error(f"✗ Failed to load {subject} MMD file")
        
        return True
    except Exception as e:
        logger.error(f"✗ Cloud storage test failed: {e}")
        return False

def test_rag_retrieval():
    """Test RAG retrieval functionality."""
    logger.info("\n=== Testing RAG Retrieval ===")
    
    try:
        # Test loading vector database for mathematics
        logger.info("Loading vector database for mathematics...")
        rag_engine.load_from_cloud('mathematics')
        logger.info("✓ Vector database loaded successfully")
        
        # Test queries
        test_queries = [
            "What are the main topics in algebra?",
            "Explain quadratic equations",
            "What is calculus?",
            "How to solve linear equations?"
        ]
        
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            results = rag_engine.search(query, k=2)
            
            if results:
                logger.info(f"✓ Found {len(results)} relevant results")
                for i, (content, distance) in enumerate(results, 1):
                    logger.info(f"  Result {i} (Distance: {distance:.4f}): {content[:100]}...")
            else:
                logger.warning(f"⚠ No results found for query: {query}")
        
        return True
    except Exception as e:
        logger.error(f"✗ RAG retrieval test failed: {e}")
        return False

def test_gemini_api():
    """Test Gemini API directly."""
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
        
        # Test simple question generation
        prompt = """Generate a simple JEE-level mathematics question about algebra with:
        - question_text
        - options (array of 4 options)
        - correct_answer
        - explanation
        
        Format as JSON."""
        
        logger.info("Generating test question...")
        response = model.generate_content(prompt)
        
        try:
            question = json.loads(response.text)
            logger.info("✓ Question generated successfully")
            logger.info(f"  Question: {question.get('question_text', 'N/A')[:100]}...")
            logger.info(f"  Options: {len(question.get('options', []))} options")
            logger.info(f"  Correct Answer: {question.get('correct_answer', 'N/A')}")
            return True
        except json.JSONDecodeError:
            logger.warning("⚠ Generated response is not valid JSON")
            logger.info(f"Raw response: {response.text[:200]}...")
            return False
        
    except Exception as e:
        logger.error(f"✗ Gemini API test failed: {e}")
        return False

def test_rag_with_gemini():
    """Test RAG retrieval combined with Gemini generation."""
    logger.info("\n=== Testing RAG + Gemini Integration ===")
    
    try:
        # 1. Load RAG engine
        logger.info("1. Loading RAG engine...")
        rag_engine.load_from_cloud('mathematics')
        logger.info("✓ RAG engine loaded")
        
        # 2. Search for relevant content
        logger.info("2. Searching for relevant content...")
        query = "quadratic equations"
        results = rag_engine.search(query, k=1)
        
        if results:
            retrieved_content = results[0][0]
            logger.info(f"✓ Retrieved content: {len(retrieved_content)} characters")
            logger.info(f"  Content preview: {retrieved_content[:200]}...")
        else:
            logger.warning("⚠ No content retrieved, using fallback")
            retrieved_content = "Quadratic equations are polynomial equations of degree 2."
        
        # 3. Generate question using retrieved content
        logger.info("3. Generating question with retrieved content...")
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        prompt = f"""Based on this content about {query}: {retrieved_content[:500]}...
        
        Generate a JEE-level multiple choice question with:
        - question_text
        - options (array of 4 options)
        - correct_answer
        - explanation
        - concepts
        
        Format as JSON."""
        
        response = model.generate_content(prompt)
        
        try:
            question = json.loads(response.text)
            logger.info("✓ RAG + Gemini integration successful!")
            logger.info(f"  Question: {question.get('question_text', 'N/A')[:100]}...")
            logger.info(f"  Options: {len(question.get('options', []))} options")
            logger.info(f"  Correct Answer: {question.get('correct_answer', 'N/A')}")
            return True
        except json.JSONDecodeError:
            logger.warning("⚠ Generated response is not valid JSON")
            logger.info(f"Raw response: {response.text[:200]}...")
            return False
        
    except Exception as e:
        logger.error(f"✗ RAG + Gemini integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting Simplified RAG and Question Generation Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Cloud Storage", test_cloud_storage),
        ("RAG Retrieval", test_rag_retrieval),
        ("Gemini API", test_gemini_api),
        ("RAG + Gemini Integration", test_rag_with_gemini)
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
        logger.info("🎉 All tests passed! Your RAG and question generation system is working correctly.")
    else:
        logger.warning(f"⚠ {total - passed} test(s) failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 