import requests
from urllib.parse import urlencode
from typing import List
from .models import Job
from .parser import IndeedParser
from .utils import get_random_headers, random_sleep, request_retry, setup_logger, resolve_redirect

logger = setup_logger("scraper")

class IndeedScraper:
    """Handles fetching pages and orchestrating scraping."""
    
    BASE_URL = "https://www.indeed.com/jobs"

    def __init__(self):
        self.parser = IndeedParser()
        self.session = requests.Session()
        # Visit homepage to set initial cookies
        try:
            headers = get_random_headers()
            self.session.get(self.BASE_URL, headers=headers, timeout=10)
            logger.info("Initialized session with cookies from indeed.com")
        except Exception as e:
            logger.warning(f"Failed to initialize session cookies: {e}")

    @request_retry
    def _fetch_page(self, url: str) -> str:
        """Fetches a single page content handling retries and headers."""
        headers = get_random_headers()
        logger.info(f"Fetching URL: {url}")
        response = self.session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text

    def scrape(self, query: str, city: str, days: int, pages: int) -> List[Job]:
        """
        Main scraping method.
        
        Args:
            query: Job search keywords
            city: Location
            days: Posted within last N days
            pages: Number of pages to scrape
            
        Returns:
            List of unique Job objects
        """
        all_jobs = []
        seen_links = set()

        for page_num in range(pages):
            start = page_num * 10
            params = {
                "q": query,
                "l": city,
                "fromage": days,
                "start": start
            }
            url = f"{self.BASE_URL}?{urlencode(params)}"
            
            try:
                html = self._fetch_page(url)
                page_jobs = self.parser.parse(html)
                
                if not page_jobs:
                    logger.warning(f"No jobs found on page {page_num + 1}. Stopping early may be necessary if consistent.")
                
                for job in page_jobs:
                    if job.link not in seen_links:
                        seen_links.add(job.link)
                        all_jobs.append(job)
                
                logger.info(f"Page {page_num + 1}/{pages} processed. Total jobs collected: {len(all_jobs)}")
                
                # Sleep between pages to be polite
                if page_num < pages - 1:
                    random_sleep()
                    
            except Exception as e:
                logger.error(f"Failed to scrape page {page_num + 1}: {e}")
        
        # Fetch full descriptions for all collected jobs
        logger.info(f"Fetching full descriptions for {len(all_jobs)} jobs...")
        for i, job in enumerate(all_jobs):
            if job.link and job.link != "N/A":
                try:
                    logger.info(f"Fetching details for job {i+1}/{len(all_jobs)}: {job.title}")
                    
                    # Manual fetch without the @retry decorator to avoid 5x retries on 403s
                    # We want to fail fast if blocked and maybe try next
                    headers = get_random_headers()
                    resp = self.session.get(job.link, headers=headers, timeout=10)
                    
                    if resp.status_code == 200:
                        detail_html = resp.text
                        job.full_description = self.parser.extract_full_description(detail_html)
                        
                        # Extract Company URL
                        job.company_url = self.parser.extract_company_url(detail_html)
                        
                        # Resolve Indeed redirect links (e.g., /rc/clk...)
                        if job.company_url and "indeed.com" in job.company_url and ("/rc/" in job.company_url or "viewjob" in job.company_url):
                             job.company_url = resolve_redirect(job.company_url, session=self.session)

                        # Check if company URL is a Workday site
                        if job.company_url and "workday" in job.company_url.lower():
                            job.is_workday = "Yes"
                        else:
                            job.is_workday = "No"
                    else:
                        logger.warning(f"Failed to fetch details (Status {resp.status_code}) for job {job.title}")
                        job.full_description = f"Error: Status {resp.status_code}"
                        
                    random_sleep() # Sleep between detail fetches
                except Exception as e:
                    logger.error(f"Failed to fetch details for job {job.title}: {e}")
                    job.full_description = "Error fetching description"
            else:
                job.full_description = "No link available"

        return all_jobs
