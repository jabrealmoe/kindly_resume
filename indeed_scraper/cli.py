import click
import pandas as pd
import json
import os
import re
from .scraper import IndeedScraper
from .utils import setup_logger
from .models import Job
from .db import SessionLocal, engine, Base
from .db_models import Job as DBJob
from sqlalchemy import text
from .llm import generate_resume, get_ollama_embedding

logger = setup_logger("cli")

def clean_sheet_name(name):
    """Cleans a string for use as an Excel sheet name."""
    # Remove invalid characters: \ / * ? : [ ]
    clean = re.sub(r'[\\/*?:\[\]]', '', name)
    # Limit to 31 characters
    return clean[:31] or "Sheet1"

@click.group()
def cli():
    """Indeed Scraper and Resume Generator CLI"""
    # Initialize the database tables if they do not exist
    Base.metadata.create_all(bind=engine)

@cli.command()
@click.option('--query', required=True, help='Job search keywords (e.g., "python developer")')
@click.option('--city', required=True, help='City name (e.g., "Atlanta, GA")')
@click.option('--days', default=7, help='Jobs posted within last N days')
@click.option('--pages', default=5, help='Number of result pages to scrape')
@click.option('--output', default='manifest.xlsx', help='Manifest file name (defaults to manifest.xlsx)')
def scrape(query, city, days, pages, output):
    """Scrapes job listings and saves to a central manifest (Excel)."""
    logger.info(f"Starting scrape: query='{query}', city='{city}', days={days}, pages={pages}")
    
    scraper = IndeedScraper()
    jobs = scraper.scrape(query=query, city=city, days=days, pages=pages)
    
    if not jobs:
        logger.warning("No jobs found. Exiting.")
        return

    # Convert to DataFrame
    job_dicts = [job.to_dict() for job in jobs]
    df = pd.DataFrame(job_dicts)
    
    # Manifest logic (Excel with sheets)
    manifest_path = output
    if not manifest_path.endswith('.xlsx'):
        manifest_path += '.xlsx'
        
    sheet_name = clean_sheet_name(query)
    
    try:
        if os.path.exists(manifest_path):
            # Load existing manifest to preserve other sheets
            with pd.ExcelWriter(manifest_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info(f"Updated sheet '{sheet_name}' in manifest '{manifest_path}'")
        else:
            # Create new manifest
            df.to_excel(manifest_path, sheet_name=sheet_name, index=False)
            logger.info(f"Created manifest '{manifest_path}' with sheet '{sheet_name}'")
            
        logger.info(f"Saved {len(jobs)} jobs for query '{query}'")
        
    except Exception as e:
        logger.error(f"Failed to save manifest to project root: {e}")
        # Fallback to /tmp if project root is somehow blocked despite initial test
        tmp_path = os.path.join('/tmp', os.path.basename(manifest_path))
        df.to_excel(tmp_path, sheet_name=sheet_name, index=False)
        logger.warning(f"Saved to /tmp instead: {tmp_path}")

@cli.command()
@click.option('--input', required=True, help='Input jobs file (Excel, CSV, or JSON)', type=click.Path(exists=True))
@click.option('--resume', required=True, help='Path to resume text file', type=click.Path(exists=True))
@click.option('--model', default=None, help='LLM model to use (defaults to LLM_MODEL env var or llama3.2)')
@click.option('--output-dir', default='output', help='Directory to save generated resumes')
@click.option('--sheet', default=None, help='Sheet name to read from if using Excel manifest')
def generate(input, resume, model, output_dir, sheet):
    """Generates resumes from an existing jobs file or manifest sheet."""
    try:
        # Load jobs
        if input.lower().endswith('.csv'):
            df = pd.read_csv(input)
        elif input.lower().endswith('.json'):
            df = pd.read_json(input)
        elif input.lower().endswith('.xlsx'):
            if sheet:
                df = pd.read_excel(input, sheet_name=sheet)
            else:
                # Default to the first sheet if not specified
                df = pd.read_excel(input)
        else:
            logger.error("Unsupported file format. Use Excel, CSV or JSON.")
            return

        # Load resume
        with open(resume, 'r', encoding='utf-8') as f:
            resume_text = f.read()

        jobs = df.to_dict('records')
        logger.info(f"Loaded {len(jobs)} jobs from {input}")
        logger.info(f"Generating optimized resumes using model '{model}' in directory '{output_dir}'...")

        for i, job in enumerate(jobs):
            # Safe access to fields
            description = job.get('full_description', '')
            title = job.get('title', 'Unknown Title')
            company = job.get('company', 'Unknown Company')
            
            if pd.isna(company) or company == "N/A": 
                 company = f"Unknown_Company_{i}"
            
            if description and isinstance(description, str) and "Description not found" not in description:
                logger.info(f"Processing resume for job {i+1}/{len(jobs)}: {title} at {company}")
                success, content = generate_resume(description, resume_text, str(company), model=model, output_dir=output_dir)
                
                if success and content:
                    # Persistence to DB
                    link = job.get('link')
                    if link:
                        with SessionLocal() as db:
                            db_job = db.query(DBJob).filter(DBJob.link == link).first()
                            if db_job:
                                db_job.generated_resume = content
                                db.commit()
                                logger.info(f"Saved resume to database for job: {title}")
                            else:
                                logger.debug(f"Job not found in database by link, skipping DB persistence: {link}")
            else:
                logger.warning(f"Skipping resume generation for job {i+1}: No description available.")

    except Exception as e:
        logger.error(f"Error during generation: {e}")

def validate_extension(filename, format):
    """Ensures filename has the correct extension."""
    base, ext = os.path.splitext(filename)
    expected_ext = f".{format}"
    if ext.lower() != expected_ext:
        return f"{base}{expected_ext}"
    return filename


def get_query_embedding(query_text: str) -> list:
    """Return a local Ollama embedding for query_text — free, no API key needed."""
    return get_ollama_embedding(query_text)

@cli.command()
@click.option('--query', required=True, help='Natural‑language query to find similar jobs')
@click.option('--top', default=5, help='Number of most similar jobs to return')
def similar(query, top):
    """Find the *top* jobs whose stored embeddings are most similar to the query.
    Uses PostgreSQL's pgvector `<=>` (cosine distance) operator.
    """
    # Compute the query embedding
    q_vec = get_query_embedding(query)
    # Run the similarity query
    import json
    with SessionLocal() as db:
        stmt = text(
            """
            SELECT id, title, company, link, array_to_json(embedding)::text::vector <=> cast(:qvec as text)::vector AS distance
            FROM jobs
            WHERE embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT :limit
            """
        )
        rows = db.execute(stmt, {"qvec": json.dumps(q_vec), "limit": top}).fetchall()
    if not rows:
        click.echo("No similar jobs found.")
        return
    click.echo(f"Top {top} similar jobs for query: '{query}'")
    for row in rows:
        click.echo(f"- [{row.distance:.4f}] {row.title} at {row.company} -> {row.link}")

@cli.command()
@click.option('--job-id', required=True, type=int, help='Database ID of the job')
@click.option('--save', is_flag=True, help='Save to file instead of printing')
def fetch_resume(job_id, save):
    """Retrieves a previously generated resume from the database."""
    with SessionLocal() as db:
        job = db.query(DBJob).filter(DBJob.id == job_id).first()
        if not job:
            click.echo(f"Job with ID {job_id} not found.")
            return
        
        if not job.generated_resume:
            click.echo(f"No generated resume found for job: {job.title}")
            return
        
        if save:
            filename = f"resume_{job_id}_{re.sub(r'[^a-zA-Z0-9]+', '_', str(job.company)).strip('_')}.md"
            output_path = os.path.join('output', filename)
            os.makedirs('output', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(job.generated_resume)
            click.echo(f"Resume saved to {output_path}")
        else:
            click.echo(f"--- Resume for {job.title} at {job.company} ---")
            click.echo(job.generated_resume)
            click.echo("--- End of Resume ---")

if __name__ == '__main__':
    cli()
