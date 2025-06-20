from cloud_config import cloud_storage
import json
import os
import logging
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_directory_structure():
    """Create the necessary directory structure in the bucket."""
    try:
        # Create static directory
        static_blob = cloud_storage.bucket.blob('static/')
        static_blob.upload_from_string('')
        logger.info("Created static directory")

        # Create vector_db directory
        vector_db_blob = cloud_storage.bucket.blob('vector_db/')
        vector_db_blob.upload_from_string('')
        logger.info("Created vector_db directory")
        
        return True
    except Exception as e:
        logger.error(f"Error creating directory structure: {e}")
        return False

def upload_mmd_files():
    """Upload the actual MMD files from the data/content directory."""
    mmd_files = {
        'mathematics': 'math.mmd',
        'physics': 'physics.mmd',
        'chemistry': 'chemistry.mmd'
    }
    
    for subject, filename in mmd_files.items():
        try:
            local_path = os.path.join('data', 'content', filename)
            if not os.path.exists(local_path):
                logger.error(f"File not found: {local_path}")
                continue
                
            # Upload the file using the correct filename
            blob = cloud_storage.bucket.blob(f'static/{filename}')
            blob.upload_from_filename(local_path)
            logger.info(f"Uploaded {filename} to bucket")
        except Exception as e:
            logger.error(f"Error uploading {filename}: {e}")

def upload_json_files():
    """Upload the JSON files from the data directory."""
    try:
        # Upload questions
        questions_path = os.path.join('data', 'questions', 'original_questions.json')
        if os.path.exists(questions_path):
            blob = cloud_storage.bucket.blob('static/original_questions.json')
            blob.upload_from_filename(questions_path)
            logger.info("Uploaded original_questions.json")
        else:
            logger.warning("original_questions.json not found in data/questions/")

        # Upload topic distribution
        dist_path = os.path.join('data', 'distributions', 'dist_topic.json')
        if os.path.exists(dist_path):
            blob = cloud_storage.bucket.blob('static/dist_topic.json')
            blob.upload_from_filename(dist_path)
            logger.info("Uploaded dist_topic.json")
        else:
            logger.warning("dist_topic.json not found in data/distributions/")
    except Exception as e:
        logger.error(f"Error uploading JSON files: {e}")

def main():
    """Set up the bucket with all necessary files."""
    logger.info("Starting bucket setup...")
    
    # Create directory structure
    if not create_directory_structure():
        logger.error("Failed to create directory structure")
        return
    
    # Upload actual MMD files
    upload_mmd_files()
    
    # Upload JSON files
    upload_json_files()
    
    logger.info("Bucket setup completed!")

if __name__ == "__main__":
    main() 