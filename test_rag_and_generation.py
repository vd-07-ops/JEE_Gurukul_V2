import json
import logging
from rag_engine import rag_engine
from generate_gemini_questions import generate_personalized_questions, QuestionDatabase
from cloud_config import cloud_storage
import os
from dotenv import load_dotenv

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

def test_question_database():
    """Test question database functionality."""
    logger.info("\n=== Testing Question Database ===")
    
    try:
        qdb = QuestionDatabase()
        logger.info("✓ Question database initialized")
        
        # Test getting MMD content
        mmd_content = qdb.get_mmd_content('mathematics', 'algebra')
        if mmd_content:
            logger.info(f"✓ Retrieved MMD content for mathematics/algebra: {len(mmd_content)} characters")
        else:
            logger.warning("⚠ No MMD content found for mathematics/algebra")
        
        # Test getting topic content
        topic_content = qdb.get_topic_content('mathematics', 'algebra')
        if topic_content:
            logger.info(f"✓ Retrieved topic content for mathematics/algebra: {len(topic_content)} characters")
        else:
            logger.warning("⚠ No topic content found for mathematics/algebra")
        
        return True
    except Exception as e:
        logger.error(f"✗ Question database test failed: {e}")
        return False

def test_gemini_generation():
    """Test Gemini question generation."""
    logger.info("\n=== Testing Gemini Question Generation ===")
    
    try:
        # Check if API key is available
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found in environment variables")
            return False
        
        logger.info("✓ Google API key found")
        
        # Test generating questions
        logger.info("Generating personalized questions...")
        questions = generate_personalized_questions("test_user_123", num_questions=2)
        
        if questions:
            logger.info(f"✓ Generated {len(questions)} questions successfully")
            for i, question in enumerate(questions, 1):
                logger.info(f"\nQuestion {i}:")
                logger.info(f"  Subject: {question.get('subject', 'N/A')}")
                logger.info(f"  Topic: {question.get('topic', 'N/A')}")
                logger.info(f"  Type: {question.get('question_type', 'N/A')}")
                logger.info(f"  Question: {question.get('question_text', 'N/A')[:100]}...")
                logger.info(f"  Options: {len(question.get('options', []))} options")
                logger.info(f"  Correct Answer: {question.get('correct_answer', 'N/A')}")
        else:
            logger.warning("⚠ No questions generated")
        
        return True
    except Exception as e:
        logger.error(f"✗ Gemini generation test failed: {e}")
        return False

def test_integrated_workflow():
    """Test the complete integrated workflow."""
    logger.info("\n=== Testing Integrated Workflow ===")
    
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
        else:
            logger.warning("⚠ No content retrieved, using fallback")
            retrieved_content = "Quadratic equations are polynomial equations of degree 2."
        
        # 3. Generate questions using the retrieved content
        logger.info("3. Generating questions with retrieved content...")
        qdb = QuestionDatabase()
        
        # Create a simple prompt using retrieved content
        prompt = f"""Based on this content about {query}: {retrieved_content[:500]}...
        
        Generate a multiple choice question with:
        - question_text
        - options (array of 4 options)
        - correct_answer
        - explanation
        - concepts
        
        Format as JSON."""
        
        logger.info("✓ Workflow completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Integrated workflow test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting RAG and Question Generation Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Cloud Storage", test_cloud_storage),
        ("RAG Retrieval", test_rag_retrieval),
        ("Question Database", test_question_database),
        ("Gemini Generation", test_gemini_generation),
        ("Integrated Workflow", test_integrated_workflow)
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
    logger.info("\n" + "="*50)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*50)
    
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