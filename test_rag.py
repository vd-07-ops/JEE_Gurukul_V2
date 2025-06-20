from rag_engine import rag_engine
import logging
import secrets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rag_engine():
    """Test the RAG engine with a sample query."""
    try:
        # Load the vector database for mathematics
        logger.info("Loading vector database for mathematics...")
        rag_engine.load_from_cloud('mathematics')
        
        # Test query
        query = "What are the main topics in algebra?"
        logger.info(f"Testing query: {query}")
        
        # Get results
        results = rag_engine.search(query, k=3)
        
        # Print results
        logger.info("\nSearch Results:")
        for i, (content, distance) in enumerate(results, 1):
            logger.info(f"\nResult {i} (Distance: {distance:.4f}):")
            logger.info(f"Content: {content[:200]}...")  # Show first 200 chars
            
        return True
    except Exception as e:
        logger.error(f"Error testing RAG engine: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting RAG engine test...")
    test_rag_engine()
    logger.info("Test completed!")

print(secrets.token_hex(32)) 