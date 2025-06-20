from cloud_config import cloud_storage
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cloud_connection():
    """Test the connection to Google Cloud Storage."""
    try:
        # Try to list files in the bucket
        bucket = cloud_storage.bucket
        blobs = list(bucket.list_blobs(max_results=1))
        logger.info("Successfully connected to Google Cloud Storage!")
        logger.info(f"Bucket name: {bucket.name}")
        return True
    except Exception as e:
        logger.error(f"Error connecting to Google Cloud Storage: {e}")
        return False

def test_mmd_files():
    """Test accessing MMD files."""
    subjects = ['mathematics', 'physics', 'chemistry']
    for subject in subjects:
        try:
            content = cloud_storage.get_mmd_content(subject)
            if content:
                logger.info(f"Successfully accessed {subject} MMD file")
            else:
                logger.warning(f"No content found for {subject} MMD file")
        except Exception as e:
            logger.error(f"Error accessing {subject} MMD file: {e}")

def main():
    """Run all tests."""
    logger.info("Starting cloud setup tests...")
    
    # Test cloud connection
    if not test_cloud_connection():
        logger.error("Cloud connection test failed!")
        return
    
    # Test MMD files
    test_mmd_files()
    
    logger.info("All tests completed!")

if __name__ == "__main__":
    main() 