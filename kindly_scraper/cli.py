import click
import pandas as pd
import json
import os
import re
from .scraper import KindlyScraper
from .utils import setup_logger
from .models import Job
from .db import SessionLocal, engine, Base
from .db_models import Job as DBJob
from sqlalchemy import text
from .llm import semantic_resume_alignment, get_ollama_embedding

logger = setup_logger("cli")

def clean_sheet_name(name):
    """Cleans a string for use as an Excel sheet name."""
    # Remove invalid characters: \ / * ? : [ ]
    clean = re.sub(r'[\\/*?:\[\]]', '', name)
    # Limit to 31 characters
    return clean[:31] or "Sheet1"

@click.group()
def cli():
    """Kindly Scraper and Semantic Alignment CLI"""
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
    
    scraper = KindlyScraper()
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
@click.option('--output-dir', default='output', help='Directory to save aligned resumes')
@click.option('--sheet', default=None, help='Sheet name to read from if using Excel manifest')
def align(input, resume, model, output_dir, sheet):
    """Semantically aligns your resume with job descriptions."""
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
        logger.info(f"Performing semantic alignment using model '{model}' in directory '{output_dir}'...")

        for i, job in enumerate(jobs):
            # Safe access to fields
            description = job.get('full_description', '')
            title = job.get('title', 'Unknown Title')
            company = job.get('company', 'Unknown Company')
            
            if pd.isna(company) or company == "N/A": 
                 company = f"Unknown_Company_{i}"
            
            if description and isinstance(description, str) and "Description not found" not in description:
                logger.info(f"Aligning resume for job {i+1}/{len(jobs)}: {title} at {company}")
                success, content = semantic_resume_alignment(description, resume_text, str(company), model=model, output_dir=output_dir)
                
                if success and content:
                    # Persistence to DB
                    link = job.get('link')
                    if link:
                        with SessionLocal() as db:
                            db_job = db.query(DBJob).filter(DBJob.link == link).first()
                            if db_job:
                                db_job.generated_resume = content
                                db.commit()
                                logger.info(f"Saved aligned resume to database for job: {title}")
                            else:
                                logger.debug(f"Job not found in database by link, skipping DB persistence: {link}")
            else:
                logger.warning(f"Skipping semantic alignment for job {i+1}: No description available.")

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
@click.option('--query', required=True, help='Natural-language query to find similar jobs')
@click.option('--top', default=5, help='Number of most similar jobs to return')
def similar(query, top):
    """Find the *top* jobs whose stored embeddings are most similar to the query."""
    # Enrich the query with the same context prefixes used during storage
    # This helps match the "Company: X\nTitle: Y" format in the database
    search_query = f"Company: {query}\nTitle: {query}\nDescription: {query}"
    q_vec = get_query_embedding(search_query)
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
        click.echo(f"- [{row.distance:.4f}] {row.id}: {row.title} at {row.company} -> {row.link}")

@cli.command()
@click.option('--limit', default=10, help='Number of jobs to list')
@click.option('--company', help='Filter by company name (partial match)')
@click.option('--query-search', help='Filter by the original search query')
def list_jobs(limit, company, query_search):
    """Lists jobs stored in the database."""
    with SessionLocal() as db:
        query = db.query(DBJob)
        if company:
            query = query.filter(DBJob.company.ilike(f"%{company}%"))
        if query_search:
            query = query.filter(DBJob.query.ilike(f"%{query_search}%"))
        
        jobs = query.order_by(DBJob.id.desc()).limit(limit).all()
        
        if not jobs:
            click.echo("No jobs found matching criteria.")
            return
        
        click.echo(f"{'ID':<5} | {'Title':<40} | {'Company':<25}")
        click.echo("-" * 75)
        for job in jobs:
            title = (job.title[:37] + '...') if len(job.title) > 40 else job.title
            company_name = (job.company[:22] + '...') if job.company and len(job.company) > 25 else (job.company or "N/A")
            click.echo(f"{job.id:<5} | {title:<40} | {company_name:<25}")

@cli.command()
@click.argument('job_id', type=int)
def describe(job_id):
    """Shows full details for a specific job ID."""
    with SessionLocal() as db:
        job = db.query(DBJob).filter(DBJob.id == job_id).first()
        if not job:
            click.echo(f"Job {job_id} not found.")
            return
        
        click.echo(f"\n=== Job {job.id}: {job.title} ===")
        click.echo(f"Company:  {job.company}")
        click.echo(f"Location: {job.location}")
        click.echo(f"Salary:   {job.salary if hasattr(job, 'salary') else 'N/A'}")
        click.echo(f"Posted:   {job.posted_date}")
        click.echo(f"Link:     {job.link}")
        click.echo(f"Query:    {job.query}")
        click.echo("\n--- Description ---")
        desc = job.full_description or "No description available."
        click.echo(desc[:2000] + ("..." if len(desc) > 2000 else ""))
        if job.generated_resume:
            click.echo("\n[AI Resume Generated: YES (use fetch-resume to see it)]")
        else:
            click.echo("\n[AI Resume Generated: NO]")

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
