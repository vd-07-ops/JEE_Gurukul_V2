from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
import os

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print('GOOGLE_API_KEY not found in environment!')
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

prompt = "Generate a simple JEE-level mathematics question about algebra. Format: QUESTION: ... OPTION A: ... OPTION B: ... OPTION C: ... OPTION D: ... CORRECT ANSWER: ... SOLUTION: ..."

try:
    response = model.generate_content(prompt)
    print("\n===== RAW GEMINI RESPONSE =====\n" + response.text + "\n==============================\n")
except Exception as e:
    print(f"Error calling Gemini API: {e}") 