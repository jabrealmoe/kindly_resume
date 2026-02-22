import logging
import random
import time
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

# Configure logging
def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)  # Set to DEBUG to see full prompts
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

logger = setup_logger("utils")

def get_random_headers():
    """Generates a random User-Agent header."""
    ua = UserAgent()
    try:
        user_agent = ua.random
    except Exception:
        # Fallback if fake_useragent fails
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    return {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Referer": "https://www.indeed.com/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def random_sleep(min_seconds=3, max_seconds=7):
    """Sleeps for a random interval."""
    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sleeping for {sleep_time:.2f} seconds...")
    time.sleep(sleep_time)

# Retry decorator configuration
# Retries on RequestException, stops after 5 attempts, waits 2^x * 1 seconds between retries
request_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.RequestException),
    before_sleep=lambda retry_state: logger.warning(f"Request failed, retrying... (Attempt {retry_state.attempt_number})")
)

def resolve_redirect(url: str, session=None) -> str:
    """Follows redirects to get the final destination URL."""
    try:
        if not session:
            session = requests.Session()
            
        # Use simple headers for redirect check
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        logger.info(f"Resolving redirect for: {url}")
        # Use GET with stream=True to avoid downloading body, just follow headers
        response = session.get(url, headers=headers, allow_redirects=True, timeout=10, stream=True)
        final_url = response.url
        response.close() # Close connection
        
        if final_url != url:
            logger.info(f"Resolved to: {final_url}")
            
        return final_url
    except Exception as e:
        logger.error(f"Error resolving redirect for {url}: {e}")
        return url
