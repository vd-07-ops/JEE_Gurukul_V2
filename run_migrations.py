import os
import logging
from app import app, db
from sqlalchemy.exc import SQLAlchemyError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
logger = logging.getLogger(__name__)

def initialize_database():
    """
    Initializes the database by creating all tables.
    Includes robust logging and error handling.
    """
    logger.info("Starting database initialization...")
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI')

    if not database_url:
        logger.error("DATABASE_URL is not set. Cannot initialize database.")
        return

    # For security, don't log the full URL if it contains credentials
    if "@" in database_url:
        safe_url = '...'.join(database_url.split('@'))
        logger.info(f"Target database: {safe_url}")
    else:
        logger.info(f"Target database: {database_url}")

    try:
        with app.app_context():
            logger.info("Application context acquired. Attempting to create all tables...")
            db.create_all()
            logger.info("db.create_all() executed successfully.")
        logger.info("Database initialization finished.")
    except SQLAlchemyError as e:
        logger.error(f"A SQLAlchemy error occurred during initialization: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during initialization: {e}", exc_info=True)

if __name__ == "__main__":
    initialize_database() 