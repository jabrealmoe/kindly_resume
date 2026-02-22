import click
import pandas as pd
import json
import os
import re
from .scraper import IndeedScraper
from .utils import setup_logger
from .models import Job

from .llm import generate_resume

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
    pass

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
                generate_resume(description, resume_text, str(company), model=model, output_dir=output_dir)
            else:
                logger.warning(f"Skipping resume generation for job {i+1}: No description available.")

    except Exception as e:
        logger.error(f"Error during generation: {e}")

if __name__ == '__main__':
    cli()
