import os

# ------------------ Ollama LLM Configuration ------------------ #
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:8b-instruct")  

# ------------------ Data Paths ------------------ #
DATA_DIR = "data"
ORIGINAL_QUESTIONS_PATH = os.path.join(DATA_DIR, "original_questions.json")
TOPIC_DISTRIBUTION_PATH = os.path.join(DATA_DIR, "topic_distribution.json")
JEE_SYLLABUS_PATH = os.path.join(DATA_DIR, "jee_syllabus.txt")
PROCESSED_QUESTIONS_DB = "processed_questions.db"  

# ------------------ ChromaDB Configuration ------------------ #
CHROMADB_PERSIST_DIR = "chroma_db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" 

# ------------------ Web Search Configuration ------------------ #
# Using DuckDuckGo
USE_SEARCH_API = True
SEARCH_API_PROVIDER = "duckduckgo"         
SEARCH_API_KEY = ""                        
MAX_SEARCH_RESULTS = 5
SEARCH_DELAY_SECONDS = 5                   

# ------------------ Quiz Configuration ------------------ #
QUIZ_QUESTION_COUNT = 25
MCQ_PERCENTAGE = 0.8
NVQ_PERCENTAGE = 0.2

# ------------------ Semantic Deduplication ------------------ #
DEDUPLICATION_THRESHOLD = 0.85
