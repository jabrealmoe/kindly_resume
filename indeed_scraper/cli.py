import click
import pandas as pd
import json
import os
from .scraper import IndeedScraper
from .utils import setup_logger
from .models import Job

from .llm import generate_resume

logger = setup_logger("cli")

@click.group()
def cli():
    """Indeed Scraper and Resume Generator CLI"""
    pass

@cli.command()
@click.option('--query', required=True, help='Job search keywords (e.g., "python developer")')
@click.option('--city', required=True, help='City name (e.g., "Atlanta, GA")')
@click.option('--days', default=7, help='Jobs posted within last N days')
@click.option('--pages', default=5, help='Number of result pages to scrape')
@click.option('--output', default='jobs.csv', help='Output file name')
@click.option('--format', type=click.Choice(['csv', 'json'], case_sensitive=False), default='csv', help='Output format')
def scrape(query, city, days, pages, output, format):
    """Scrapes job listings and saves to file."""
    logger.info(f"Starting scrape: query='{query}', city='{city}', days={days}, pages={pages}")
    
    scraper = IndeedScraper()
    jobs = scraper.scrape(query=query, city=city, days=days, pages=pages)
    
    if not jobs:
        logger.warning("No jobs found. Exiting.")
        return

    # Convert to DataFrame
    job_dicts = [job.to_dict() for job in jobs]
    df = pd.DataFrame(job_dicts)
    
    # Export
    output = validate_extension(output, format)
    
    # If output is just a filename, put it in 'output'
    if not os.path.dirname(output):
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output = os.path.join(output_dir, output)
    else:
        # Ensure the specified directory exists
        os.makedirs(os.path.dirname(output), exist_ok=True)

    if format == 'csv':
        df.to_csv(output, index=False)
        logger.info(f"Saved {len(jobs)} jobs to {output}")
    elif format == 'json':
        df.to_json(output, orient='records', indent=2)
        logger.info(f"Saved {len(jobs)} jobs to {output}")

@cli.command()
@click.option('--input', required=True, help='Input jobs file (CSV or JSON)', type=click.Path(exists=True))
@click.option('--resume', required=True, help='Path to resume text file', type=click.Path(exists=True))
@click.option('--model', default='llama3.2', help='Ollama model to use')
@click.option('--output-dir', default='output', help='Directory to save generated resumes')
def generate(input, resume, model, output_dir):
    """Generates resumes from an existing jobs file."""
    try:
        # Load jobs
        if input.lower().endswith('.csv'):
            df = pd.read_csv(input)
        elif input.lower().endswith('.json'):
            df = pd.read_json(input)
        else:
            logger.error("Unsupported file format. Use CSV or JSON.")
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
                generate_resume(description, resume_text, str(company), model=model, output_dir=output_dir)
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

if __name__ == '__main__':
    cli()
