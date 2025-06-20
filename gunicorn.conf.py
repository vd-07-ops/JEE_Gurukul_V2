"""Gunicorn configuration file."""
import logging
import sys

# This hook is run once in the master Gunicorn process.
def on_starting(server):
    server.log.info("Gunicorn master process is starting.")
    server.log.info("This is the final, correct database initialization method.")

# This hook is run in each worker process after it has been forked.
def post_fork(server, worker):
    worker.log.info(f"Worker process (pid: {worker.pid}) has been forked.")
    
    # Wrap the entire database initialization in a try-except block
    # to catch any possible error and log it.
    try:
        worker.log.info("Attempting to import app and db in worker process...")
        from app import app, db
        worker.log.info("Successfully imported app and db.")

        with app.app_context():
            worker.log.info("Worker has acquired the application context.")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            worker.log.info("Checking for database tables in worker process...")
            if not inspector.has_table("user"):
                worker.log.info("--> 'user' table not found. Creating all tables now...")
                db.create_all()
                worker.log.info("--> All database tables created successfully in worker.")
            else:
                worker.log.info("--> 'user' table already exists. No action needed.")

    except Exception as e:
        # If any exception occurs, log it directly to the worker's log.
        worker.log.error(f"!!!!!! An unexpected error occurred in the post_fork hook: {e}", exc_info=True)
        # It's critical to exit if we can't set up the DB, to prevent a broken worker from running.
        sys.exit(1) 