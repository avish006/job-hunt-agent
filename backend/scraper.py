import logging
from typing import List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)

class BaseJobScraper:
    """Base class for all job scrapers."""
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

class LinkedInPlaywrightScraper(BaseJobScraper):
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"Using Playwright to scrape LinkedIn for '{keywords}' in '{location}'")
        from playwright.sync_api import sync_playwright
        import urllib.parse
        from bs4 import BeautifulSoup
        
        jobs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Format URL
                base_url = "https://www.linkedin.com/jobs/search"
                params = {
                    "keywords": keywords,
                    "location": location,
                    "f_TPR": "r86400" # Past 24 hours
                }
                url = f"{base_url}?{urllib.parse.urlencode(params)}"
                
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                job_cards = soup.find_all('div', class_='base-card')
                
                for card in job_cards[:15]:
                    title_elem = card.find('h3', class_='base-search-card__title')
                    company_elem = card.find('h4', class_='base-search-card__subtitle')
                    location_elem = card.find('span', class_='job-search-card__location')
                    link_elem = card.find('a', class_='base-card__full-link')
                    
                    raw_url = link_elem['href'] if link_elem else "N/A"
                    import re
                    url = re.sub(r'https://[a-z]{2}\.linkedin\.com', 'https://www.linkedin.com', raw_url)
                    
                    if title_elem and company_elem:
                        jobs.append({
                            "title": title_elem.text.strip(),
                            "company": company_elem.text.strip(),
                            "location": location_elem.text.strip() if location_elem else "Unknown",
                            "url": url,
                            "description": "Scraped via Playwright",
                            "source": "Playwright"
                        })
                
                browser.close()
        except Exception as e:
            logger.error(f"Playwright scraping failed: {e}")
            
        return jobs

class JobSpyScraper(BaseJobScraper):
    def __init__(self, site_name: str):
        self.site_name = site_name
        
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"Using JobSpy to scrape {self.site_name} for '{keywords}' in '{location}'")
        from jobspy import scrape_jobs
        jobs = []
        try:
            df = scrape_jobs(
                site_name=[self.site_name],
                search_term=keywords,
                location=location,
                results_wanted=15
            )
            
            if df is not None and not df.empty:
                df = df.fillna("")
                for _, row in df.iterrows():
                    jobs.append({
                        "title": str(row.get("title", "Unknown Title") or ""),
                        "company": str(row.get("company", "Unknown Company") or ""),
                        "location": str(row.get("location", location) or ""),
                        "url": str(row.get("job_url", "") or ""),
                        "description": str(row.get("description", ""))[:200] + "..." if pd.notna(row.get("description")) else "Scraped via JobSpy",
                        "source": "JobSpy"
                    })
        except Exception as e:
            logger.error(f"JobSpy scraping failed for {self.site_name}: {e}")
            
        return jobs

class JobAggregator:
    def __init__(self):
        # Initialize all scrapers
        self.scrapers = [
            LinkedInPlaywrightScraper(),
            JobSpyScraper(site_name="indeed"),
            JobSpyScraper(site_name="linkedin")
        ]
        
    def search_all(self, keywords: str, location: str) -> List[Dict[str, Any]]:
        all_jobs = []
        
        # 1. Collect from standard scrapers
        for scraper in self.scrapers:
            results = scraper.search(keywords, location)
            all_jobs.extend(results)
            
        # 2. Collect from MCP Server
        try:
            from mcp_client import run_mcp_search
            # Provide a rich query string for DuckDuckGo
            mcp_query = f"{keywords} jobs in {location}"
            logger.info(f"Using MCP Client to search web for '{mcp_query}'")
            mcp_jobs = run_mcp_search(mcp_query)
            if isinstance(mcp_jobs, list):
                all_jobs.extend(mcp_jobs)
        except Exception as e:
            logger.error(f"MCP Search failed: {e}")
            
        # 3. Deduplicate by checking lowercase title + company
        seen_keys = set()
        deduped_jobs = []
        
        for job in all_jobs:
            if "error" in job:
                continue
                
            title_str = str(job.get('title', ''))
            company_str = str(job.get('company', ''))
            key = f"{title_str.lower()}|{company_str.lower()}"
            if key not in seen_keys and key != "|":
                seen_keys.add(key)
                deduped_jobs.append(job)
                
        return deduped_jobs
