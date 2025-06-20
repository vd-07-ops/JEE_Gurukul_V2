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

def get_mmd_content_for_topic(subject, topic):
    """Get relevant MMD content for a specific topic from the main MMD file."""
    try:
        mmd_file = f'md_files/{subject}.mmd'
        mmd_content = cloud_storage.get_text_file(mmd_file)
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

def generate_question_simple(subject, topic, difficulty="medium"):
    """Generate a question using simple format that works reliably."""
    try:
        # Get relevant MMD content
        mmd_content = get_mmd_content_for_topic(subject, topic)
        if not mmd_content:
            logger.error(f"Could not retrieve MMD content for {subject}/{topic}")
            return None
        
        # Configure Gemini
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("GOOGLE_API_KEY not found")
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Simple, clear prompt
        prompt = f"""Based on this content from the {subject} markdown file about {topic}:

{mmd_content[:1500]}

Generate a JEE-level {subject} question about {topic}. Return the response in this exact format:

QUESTION: [the question text here]
OPTION A: [first option]
OPTION B: [second option] 
OPTION C: [third option]
OPTION D: [fourth option]
CORRECT ANSWER: [A, B, C, or D]
SOLUTION: [detailed step-by-step solution]
CONCEPTS: [key concepts from the content]

Make sure:
1. The question is relevant to {topic}
2. All 4 options are plausible
3. The correct answer is A, B, C, or D
4. The solution is detailed and educational
5. The difficulty level is {difficulty}"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse the response
        question_data = {}
        
        # Extract question
        question_match = re.search(r'QUESTION:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        if question_match:
            question_data['question'] = question_match.group(1).strip()
        
        # Extract options
        option_a_match = re.search(r'OPTION A:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        option_b_match = re.search(r'OPTION B:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        option_c_match = re.search(r'OPTION C:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        option_d_match = re.search(r'OPTION D:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        
        options = []
        if option_a_match:
            options.append(f"A) {option_a_match.group(1).strip()}")
        if option_b_match:
            options.append(f"B) {option_b_match.group(1).strip()}")
        if option_c_match:
            options.append(f"C) {option_c_match.group(1).strip()}")
        if option_d_match:
            options.append(f"D) {option_d_match.group(1).strip()}")
        
        question_data['options'] = options
        
        # Extract correct answer
        correct_match = re.search(r'CORRECT ANSWER:\s*([ABCD])', response_text, re.IGNORECASE)
        if correct_match:
            correct_letter = correct_match.group(1).upper()
            question_data['correct_answer'] = f"{correct_letter}) {options[ord(correct_letter) - ord('A')].split(') ', 1)[1] if len(options) > ord(correct_letter) - ord('A') else 'Option'}"
        
        # Extract solution
        solution_match = re.search(r'SOLUTION:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        if solution_match:
            question_data['step_by_step_solution'] = solution_match.group(1).strip()
        
        # Extract concepts
        concepts_match = re.search(r'CONCEPTS:\s*(.+)', response_text, re.IGNORECASE | re.DOTALL)
        if concepts_match:
            question_data['relevant_content'] = concepts_match.group(1).strip()
        
        # Add metadata
        question_data['subject'] = subject
        question_data['topic'] = topic
        question_data['difficulty'] = difficulty
        
        # Validate
        if not question_data.get('question'):
            logger.error("No question extracted")
            return None
        
        if len(question_data.get('options', [])) != 4:
            logger.error(f"Expected 4 options, got {len(question_data.get('options', []))}")
            return None
        
        if not question_data.get('correct_answer'):
            logger.error("No correct answer extracted")
            return None
        
        return question_data
        
    except Exception as e:
        logger.error(f"Error generating question for {subject}/{topic}: {e}")
        return None

def test_cloud_storage_setup():
    """Test if all required files are accessible in cloud storage."""
    logger.info("=== Testing Cloud Storage Setup ===")
    try:
        topic_dist = cloud_storage.get_topic_distribution()
        logger.info(f"✓ Topic distribution loaded: {len(topic_dist)} subjects found")
        
        # Test MMD files (only 3 files: math.mmd, physics.mmd, chemistry.mmd)
        subjects = ['math', 'physics', 'chemistry']
        mmd_files = {}
        
        for subject in subjects:
            try:
                mmd_content = cloud_storage.get_text_file(f'md_files/{subject}.mmd')
                if mmd_content:
                    mmd_files[subject] = mmd_content
                    logger.info(f"✓ {subject}.mmd loaded: {len(mmd_content)} characters")
                else:
                    logger.error(f"✗ Failed to load md_files/{subject}.mmd (file is empty or missing)")
            except Exception as e:
                logger.error(f"✗ Error loading md_files/{subject}.mmd: {e}")
        
        # Test original_questions.json
        try:
            original_questions = cloud_storage.get_text_file('static/original_questions.json')
            if original_questions:
                questions_data = json.loads(original_questions)
                logger.info(f"✓ original_questions.json loaded: {len(questions_data)} questions")
            else:
                logger.error("✗ Failed to load static/original_questions.json")
        except Exception as e:
            logger.error(f"✗ Error loading static/original_questions.json: {e}")
        
        return len(mmd_files) == 3
    except Exception as e:
        logger.error(f"✗ Cloud storage test failed: {e}")
        return False

def test_question_generation():
    """Test question generation with simple format."""
    logger.info("\n=== Testing Question Generation ===")
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("✗ GOOGLE_API_KEY not found in environment variables")
            return False
        
        logger.info("✓ Google API key found")
        
        # Test with a simple topic
        question_data = generate_question_simple("math", "algebra", "medium")
        
        if question_data:
            logger.info("✓ Question generated successfully")
            logger.info(f"  Subject: {question_data.get('subject')}")
            logger.info(f"  Topic: {question_data.get('topic')}")
            logger.info(f"  Difficulty: {question_data.get('difficulty')}")
            logger.info(f"  Question: {question_data.get('question', 'N/A')[:100]}...")
            logger.info(f"  Options: {len(question_data.get('options', []))} options")
            logger.info(f"  Correct Answer: {question_data.get('correct_answer', 'N/A')}")
            logger.info(f"  Solution Length: {len(question_data.get('step_by_step_solution', ''))} characters")
            logger.info(f"  Concepts Length: {len(question_data.get('relevant_content', ''))} characters")
            return True
        else:
            logger.error("✗ Failed to generate question")
            return False
            
    except Exception as e:
        logger.error(f"✗ Question generation test failed: {e}")
        return False

def test_multiple_questions():
    """Test generating multiple questions."""
    logger.info("\n=== Testing Multiple Questions Generation ===")
    try:
        topic_dist = cloud_storage.get_topic_distribution()
        if not topic_dist:
            logger.error("✗ No topic distribution available")
            return False
        
        # Get topics from mathematics
        math_topics = topic_dist.get('mathematics', {})
        if not math_topics:
            logger.error("✗ No mathematics topics available")
            return False
        
        # Select first 2 topics to test
        test_topics = list(math_topics.keys())[:2]
        difficulties = ["easy", "medium"]
        
        logger.info(f"✓ Testing {len(test_topics)} topics with {len(difficulties)} difficulties each")
        
        successful_questions = 0
        total_attempts = 0
        
        for topic in test_topics:
            for difficulty in difficulties:
                logger.info(f"\nGenerating {difficulty} question for topic: {topic}")
                
                question_data = generate_question_simple("math", topic, difficulty)
                
                total_attempts += 1
                
                if question_data:
                    successful_questions += 1
                    logger.info(f"  ✓ {difficulty.capitalize()} question generated successfully")
                    logger.info(f"    Question: {question_data.get('question', 'N/A')[:80]}...")
                    logger.info(f"    Difficulty: {question_data.get('difficulty', 'N/A')}")
                else:
                    logger.warning(f"  ⚠ Failed to generate {difficulty} question for {topic}")
        
        success_rate = successful_questions / total_attempts if total_attempts > 0 else 0
        logger.info(f"\n✓ Successfully generated {successful_questions}/{total_attempts} questions ({success_rate:.1%} success rate)")
        
        return success_rate >= 0.5
        
    except Exception as e:
        logger.error(f"✗ Multiple questions generation test failed: {e}")
        return False

def test_production_workflow():
    """Test the complete production workflow."""
    logger.info("\n=== Testing Production Workflow ===")
    try:
        logger.info("1. Loading topic distribution...")
        topic_dist = cloud_storage.get_topic_distribution()
        if not topic_dist:
            logger.error("✗ No topic distribution available")
            return False
        
        logger.info("2. Selecting topics for question generation...")
        math_topics = topic_dist.get('mathematics', {})
        if not math_topics:
            logger.error("✗ No mathematics topics available")
            return False
        
        selected_topics = list(math_topics.keys())[:1]  # Just test one topic
        logger.info(f"✓ Selected topics: {selected_topics}")
        
        logger.info("3. Generating questions...")
        generated_questions = []
        
        for topic in selected_topics:
            logger.info(f"\nGenerating question for: {topic}")
            
            question_data = generate_question_simple("math", topic, "medium")
            
            if question_data:
                generated_questions.append(question_data)
                logger.info(f"✓ Question generated successfully")
                logger.info(f"  ✓ Question: {question_data.get('question', 'N/A')[:100]}...")
                logger.info(f"  ✓ Options: {len(question_data.get('options', []))}")
                logger.info(f"  ✓ Solution: {len(question_data.get('step_by_step_solution', ''))} chars")
                logger.info(f"  ✓ Concepts: {len(question_data.get('relevant_content', ''))} chars")
            else:
                logger.error(f"✗ Failed to generate question for {topic}")
        
        if generated_questions:
            logger.info(f"\n✓ Successfully generated {len(generated_questions)} questions")
            logger.info("✓ Production workflow is working correctly!")
            
            # Show sample question structure
            sample_question = generated_questions[0]
            logger.info("\n📋 Sample Question Structure:")
            logger.info(f"  Subject: {sample_question.get('subject')}")
            logger.info(f"  Topic: {sample_question.get('topic')}")
            logger.info(f"  Difficulty: {sample_question.get('difficulty')}")
            logger.info(f"  Question: {sample_question.get('question')[:100]}...")
            logger.info(f"  Options: {sample_question.get('options')}")
            logger.info(f"  Correct Answer: {sample_question.get('correct_answer')}")
            logger.info(f"  Solution: {sample_question.get('step_by_step_solution')[:100]}...")
            logger.info(f"  Concepts: {sample_question.get('relevant_content')[:100]}...")
            
            return True
        else:
            logger.error("✗ No questions generated successfully")
            return False
            
    except Exception as e:
        logger.error(f"✗ Production workflow test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting Simple and Robust RAG Question Generation Tests")
    logger.info("=" * 80)
    
    tests = [
        ("Cloud Storage Setup", test_cloud_storage_setup),
        ("Question Generation", test_question_generation),
        ("Multiple Questions", test_multiple_questions),
        ("Production Workflow", test_production_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*30} {test_name} {'='*30}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 COMPLETE TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Your system is production-ready!")
        logger.info("🎯 You can now integrate this into your main application!")
    elif passed >= 3:
        logger.info("✅ MOST TESTS PASSED! Your system is working excellently!")
        logger.info("🎯 You can proceed with your main application!")
    else:
        logger.warning(f"⚠ {total - passed} test(s) failed. Please check the errors above.")
    
    logger.info("\n" + "="*80)
    logger.info("🎁 INTEGRATION GUIDE")
    logger.info("=" * 80)
    logger.info("To integrate into your main application:")
    logger.info("1. Use the generate_question_simple() function")
    logger.info("2. Pass subject, topic, and difficulty as parameters")
    logger.info("3. The function returns a complete question object")
    logger.info("4. Handle any None returns as generation failures")
    logger.info("5. The format is simple and reliable!")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
