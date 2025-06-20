import logging
from rag_engine import rag_engine
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def build_vector_database(subject: str):
    """Build vector database for a specific subject."""
    try:
        logger.info(f"Building vector database for {subject}...")
        rag_engine.build_vector_db(subject)
        logger.info(f"Successfully built vector database for {subject}")
        return True
    except Exception as e:
        logger.error(f"Error building vector database for {subject}: {e}")
        return False

def main():
    """Build vector databases for all subjects."""
    subjects = ['mathematics', 'physics', 'chemistry']
    
    for subject in subjects:
        if not build_vector_database(subject):
            logger.error(f"Failed to build vector database for {subject}")
            sys.exit(1)
    
    logger.info("Successfully built vector databases for all subjects!")

if __name__ == "__main__":
    main() 