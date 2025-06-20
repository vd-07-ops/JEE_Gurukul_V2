import logging

# Gunicorn post_fork hook to initialize the database in each worker process.
# This is the definitive solution for ensuring the database is ready in a multi-process environment.

def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")
    
    # Import app and db within the hook to ensure it's loaded in the worker's context
    from app import app, db
    
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        worker.log.info("Checking for database tables in worker process...")
        if not inspector.has_table("user"):
            worker.log.info("Database tables not found in worker, creating them now...")
            db.create_all()
            worker.log.info("Database tables created successfully in worker.")
        else:
            worker.log.info("Database tables already exist in worker.") 