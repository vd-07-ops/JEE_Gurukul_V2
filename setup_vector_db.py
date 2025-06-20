from rag_engine import rag_engine
from cloud_config import STORAGE_PATHS
import os
from google.cloud import storage
from google.oauth2 import service_account
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_gcp_environment():
    """Set up the Google Cloud environment."""
    try:
        # Verify service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            'google_cloud_service_account.json'
        )
        storage_client = storage.Client(credentials=credentials)
        
        # Verify bucket access
        bucket = storage_client.bucket(STORAGE_PATHS['bucket_name'])
        if not bucket.exists():
            raise Exception(f"Bucket {STORAGE_PATHS['bucket_name']} does not exist")
            
        logger.info("Successfully connected to Google Cloud Storage")
        return True
    except Exception as e:
        logger.error(f"Error setting up GCP environment: {e}")
        return False

def create_vector_db_directories():
    """Create necessary directories in Google Cloud Storage."""
    try:
        # Create vector_db directory
        vector_db_path = STORAGE_PATHS['vector_db']['base_path']
        blob = bucket.blob(vector_db_path)
        blob.upload_from_string('')
        logger.info(f"Created directory: {vector_db_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directories: {e}")
        return False

def build_vector_databases():
    """Build vector databases for all subjects."""
    subjects = list(STORAGE_PATHS['mmd_files'].keys())
    
    for subject in subjects:
        try:
            logger.info(f"Building vector database for {subject}...")
            rag_engine.build_vector_db(subject)
            logger.info(f"Successfully built vector database for {subject}")
        except Exception as e:
            logger.error(f"Error building vector database for {subject}: {e}")

def verify_vector_databases():
    """Verify that vector databases are properly built and accessible."""
    subjects = list(STORAGE_PATHS['mmd_files'].keys())
    
    for subject in subjects:
        try:
            logger.info(f"Verifying vector database for {subject}...")
            rag_engine.load_from_cloud(subject)
            
            # Test search
            test_query = "test query"
            results = rag_engine.search(test_query, k=1)
            
            if results:
                logger.info(f"Successfully verified vector database for {subject}")
            else:
                logger.warning(f"Vector database for {subject} is empty")
                
        except Exception as e:
            logger.error(f"Error verifying vector database for {subject}: {e}")

def main():
    """Main setup function."""
    logger.info("Starting vector database setup...")
    
    # Step 1: Set up GCP environment
    if not setup_gcp_environment():
        logger.error("Failed to set up GCP environment")
        return
    
    # Step 2: Create necessary directories
    if not create_vector_db_directories():
        logger.error("Failed to create directories")
        return
    
    # Step 3: Build vector databases
    build_vector_databases()
    
    # Step 4: Verify vector databases
    verify_vector_databases()
    
    logger.info("Vector database setup completed!")

if __name__ == "__main__":
    main() 