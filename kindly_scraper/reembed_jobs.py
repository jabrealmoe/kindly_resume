import os
import sys

# Workaround for environment issues: programmatically add venv site-packages
venv_path = os.path.join(os.getcwd(), 'venv', 'lib', 'python3.14', 'site-packages')
print(f"DEBUG: Checking venv_path: {venv_path}")
print(f"DEBUG: Path exists? {os.path.exists(venv_path)}")
if os.path.exists(venv_path):
    sys.path.insert(0, venv_path)
    sys.path.insert(0, os.getcwd())
    print(f"DEBUG: Path added to sys.path.")

try:
    from sqlalchemy import text
    print("DEBUG: sqlalchemy imported successfully.")
except ImportError:
    print("DEBUG: Failed to import sqlalchemy.")
    sys.exit(1)
from kindly_scraper.db import SessionLocal
from kindly_scraper.db_models import Job as DBJob
from kindly_scraper.llm import get_ollama_embedding
from kindly_scraper.utils import setup_logger

logger = setup_logger("reembed")

def reembed_all():
    """Iterates through all jobs in the DB and updates embeddings with enriched context."""
    logger.info("Starting re-embedding process for all jobs...")
    
    with SessionLocal() as session:
        jobs = session.query(DBJob).all()
        total = len(jobs)
        logger.info(f"Found {total} jobs to process.")
        
        updated_count = 0
        nullified_count = 0
        error_count = 0
        
        for i, job in enumerate(jobs):
            # Check for various failure markers
            is_valid_desc = (
                job.full_description 
                and not job.full_description.startswith("Error")
                and "Description not found" not in job.full_description
            )
            
            if is_valid_desc:
                try:
                    logger.info(f"[{i+1}/{total}] Re-embedding: {job.title} at {job.company}")
                    # Combine context for better similarity search
                    embedding_text = f"Company: {job.company}\nTitle: {job.title}\nDescription: {job.full_description}"
                    vec = get_ollama_embedding(embedding_text)
                    job.embedding = vec
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to generate embedding for {job.title} (ID: {job.id}): {e}")
                    error_count += 1
            else:
                logger.warning(f"[{i+1}/{total}] Nullifying embedding for poisoned/invalid job: {job.title} (ID: {job.id})")
                job.embedding = None
                nullified_count += 1
            
            # Commit periodically or at the end
            if (i + 1) % 10 == 0:
                session.commit()
                logger.info(f"Committed progress at {i+1} jobs.")
        
        session.commit()
        logger.info(f"Re-embedding complete!")
        logger.info(f"Updated: {updated_count}")
        logger.info(f"Nullified: {nullified_count}")
        logger.info(f"Errors: {error_count}")

if __name__ == "__main__":
    reembed_all()
