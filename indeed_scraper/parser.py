from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
from .models import Job
from .utils import setup_logger

logger = setup_logger("parser")

class IndeedParser:
    """Parses Indeed job listing HTML."""
    
    BASE_URL = "https://www.indeed.com"

    def parse(self, html_content: str) -> List[Job]:
        """Parses the HTML content and returns a list of Job objects."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Indeed's job cards often have these classes. 
        # Note: Selectors are clear points of failure and may need updates.
        # Strategies: 
        # 1. Look for 'div' with class 'job_seen_beacon' (common in recent layouts)
        # 2. Look for 'td' with class 'resultContent'
        
        job_cards = soup.find_all('div', class_=lambda c: c and 'job_seen_beacon' in c)
        
        if not job_cards:
            # Fallback or different layout check
            job_cards = soup.find_all('div', class_='jobsearch-SerpJobCard')
            
        jobs = []
        for card in job_cards:
            try:
                job = self._extract_job_details(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Error parsing job card: {e}")
                continue
                
        logger.info(f"Parsed {len(jobs)} jobs from page.")
        return jobs

    def _extract_job_details(self, card) -> Optional[Job]:
        # Title
        title_elem = card.select_one('h2.jobTitle span[title]') or card.select_one('h2.jobTitle')
        title = title_elem.get_text(strip=True) if title_elem else "N/A"

        # Company
        company_elem = card.select_one('[data-testid="company-name"]') or card.select_one('.companyName')
        company = company_elem.get_text(strip=True) if company_elem else "N/A"

        # Location
        location_elem = card.select_one('[data-testid="text-location"]') or card.select_one('.companyLocation')
        location = location_elem.get_text(strip=True) if location_elem else "N/A"

        # Posted Date
        # Usually inside a span with class 'date' or under 'myJobsState'
        posted_elem = card.select_one('.date') or card.select_one('span.date')
        posted = posted_elem.get_text(strip=True) if posted_elem else "N/A"
        # Sometimes 'date' has a 'span' inside with 'visually-hidden' text, handled by get_text

        # Summary/Snippet
        # Often in a div with class 'job-snippet'
        summary_elem = card.select_one('.job-snippet')
        if summary_elem:
            summary = summary_elem.get_text(strip=True)
        else:
            # Fallback to metadataContainer (e.g. benefits, salary, attributes)
            metadata_ul = card.select_one('.metadataContainer')
            if metadata_ul:
                items = [li.get_text(strip=True) for li in metadata_ul.find_all('li')]
                summary = "; ".join(items) if items else "N/A"
            else:
                summary = "N/A"

        # Link
        # The anchor tag is usually roughly around the title
        link_elem = card.select_one('h2.jobTitle a') or card.find('a', href=True)
        link = "N/A"
        if link_elem and link_elem.get('href'):
            link = urljoin(self.BASE_URL, link_elem.get('href'))

        return Job(
            title=title,
            company=company,
            location=location,
            posted=posted,
            summary=summary,
            link=link
        )

    def extract_full_description(self, html_content: str) -> str:
        """Parses the job detail page HTML to extract the full description."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Common selector for Indeed job descriptions
        desc_elem = soup.select_one('#jobDescriptionText')
        
        if desc_elem:
            # Get text with preserved whitespace/newlines if possible, or just stripped text
            # get_text(separator='\n') helps preserve structure
            return desc_elem.get_text(separator='\n', strip=True)
            
        # Fallback for other layouts
        desc_elem = soup.select_one('.jobsearch-JobComponent-description')
        if desc_elem:
            return desc_elem.get_text(separator='\n', strip=True)
            
        return "Description not found or parsing failed."

    def extract_company_url(self, html_content: str) -> Optional[str]:
        """Extracts the 'Apply on Company Site' URL if available."""
        soup = BeautifulSoup(html_content, 'html.parser')
        url = "N/A"

        if url == "N/A":
             # Try text based search which is often more reliable
             for a in soup.find_all('a', href=True):
                 text = a.get_text(strip=True).lower()
                 if 'company site' in text or 'apply on company' in text:
                     url = a['href']
                     break

        # 1. Container with id 'applyButtonLinkContainer'
        if url == "N/A":
            container = soup.select_one('#applyButtonLinkContainer')
            if container:
                link = container.find('a', href=True)
                if link:
                    url = link['href']

        # 2. Generic 'Apply Now' button which might clear to company site
        if url == "N/A":
            apply_btn = soup.select_one('[data-testid="apply-button"]')
            if apply_btn and apply_btn.get('href'):
                url = apply_btn['href']
            
        # 3. Old style Indeed Apply or Company Site
        if url == "N/A":
            apply_btn = soup.select_one('.jobsearch-IndeedApplyButton-contentWrapper a')
            if apply_btn and apply_btn.get('href'):
                url = apply_btn['href']

        # 4. ViewJobButtons container
        if url == "N/A":
             apply_btn = soup.select_one('#jobsearch-ViewJobButtons-container a')
             if apply_btn and apply_btn.get('href'):
                 url = apply_btn['href']
            
        # 5. New Design Apply Button
        if url == "N/A":
             apply_btn = soup.select_one('span.jobsearch-IndeedApplyButton-newDesign a')
             if apply_btn and apply_btn.get('href'):
                 url = apply_btn['href']

        # 6. Generic IndeedApply Class
        if url == "N/A":
             apply_btn = soup.select_one('div.jobsearch-IndeedApplyButton a')
             if apply_btn and apply_btn.get('href'):
                 url = apply_btn['href']

        # 7. Button inside ViewJobButtons container (sometimes it is not an anchor but has data-href or onclick)
        # Note: Handling JS redirects is hard without selenium, but sometimes the url is in attributes
             
        if url != "N/A" and not url.startswith(('http:', 'https:')):
            url = urljoin(self.BASE_URL, url)
            
        return url
