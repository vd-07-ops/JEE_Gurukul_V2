from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv()

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

def test_structured_output():
    """Test the structured output approach"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment!")
        return
    
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = """Generate a JEE-level physics question about Modern Physics with difficulty medium.

Requirements:
1. Create a challenging but fair question
2. Provide exactly 4 options (A, B, C, D)
3. Include a detailed step-by-step solution
4. Ensure the correct answer is one of the options
5. Make the question relevant to quantum mechanics or atomic physics

Return a structured question with options and solution."""

        print("🔄 Generating structured question...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": QuestionData,
            },
        )
        
        # Parse the structured response
        question_data: QuestionData = response.parsed
        
        print("\n✅ STRUCTURED OUTPUT SUCCESS!")
        print("=" * 50)
        print(f"Question: {question_data.question_text}")
        print("\nOptions:")
        for opt in question_data.options:
            print(f"  {opt.id}) {opt.text}")
        print(f"\nCorrect Answer: {question_data.correct_answer}")
        print(f"Difficulty: {question_data.difficulty}")
        print(f"\nSolution: {question_data.solution}")
        print("=" * 50)
        
        # Test conversion to frontend format
        frontend_options = [f"{opt.id}) {opt.text}" for opt in question_data.options]
        print(f"\nFrontend Options: {frontend_options}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in structured output: {e}")
        return False

if __name__ == "__main__":
    test_structured_output() 