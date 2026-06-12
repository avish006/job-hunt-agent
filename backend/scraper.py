import logging
import sys
import os

# Force UTF-8 across all I/O to prevent Windows charmap crashes from unicode in crawled content
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from typing import List, Dict, Any
import pandas as pd
import requests
import feedparser
import urllib.parse
import json
import concurrent.futures

def _safe(s: str) -> str:
    """Encode string to ASCII safely to prevent Windows charmap errors in logs."""
    return s.encode('ascii', errors='replace').decode('ascii') if s else ""

logger = logging.getLogger(__name__)

# ─── TARGET JOB BOARDS (for SearxNG site: queries) ───────────────────────────
JOB_BOARDS = [
    "naukri.com",
    "internshala.com",
    "linkedin.com",
    "glassdoor.co.in",
    "glassdoor.com",
    "wellfound.com",
    "workatastartup.com",
    "indeed.com",
    "instahyre.com",
    "foundit.in",
    "monster.com",
    "unstop.com",
]

class BaseJobScraper:
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

# ─── JobSpy Scraper ────────────────────────────────────────────────────────────
class JobSpyScraper(BaseJobScraper):
    def __init__(self, site_name: str, country: str = "india"):
        self.site_name = site_name
        self.country = country

    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"JobSpy [{self.site_name}]: '{keywords}' in '{location}'")
        from jobspy import scrape_jobs
        jobs = []
        try:
            df = scrape_jobs(
                site_name=[self.site_name],
                search_term=keywords,
                location=location,
                results_wanted=30,
                country_indeed=self.country,
                is_remote="remote" in location.lower(),
            )
            if df is not None and not df.empty:
                df = df.fillna("")
                for _, row in df.iterrows():
                    desc = str(row.get("description", "") or "")
                    jobs.append({
                        "title": str(row.get("title", "") or ""),
                        "company": str(row.get("company", "") or ""),
                        "location": str(row.get("location", location) or ""),
                        "url": str(row.get("job_url", "") or ""),
                        "description": (desc[:500] + "...") if desc else "No description.",
                        "source": f"JobSpy/{self.site_name.capitalize()}"
                    })
        except Exception as e:
            logger.error(f"JobSpy [{self.site_name}] failed: {e}")
        logger.info(f"JobSpy [{self.site_name}]: {len(jobs)} results")
        return jobs

# ─── LinkedIn Playwright Scraper ───────────────────────────────────────────────
class LinkedInPlaywrightScraper(BaseJobScraper):
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"Playwright [LinkedIn]: '{keywords}' in '{location}'")
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        import re
        jobs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                params = {"keywords": keywords, "location": location, "f_TPR": "r604800"}
                url = f"https://www.linkedin.com/jobs/search?{urllib.parse.urlencode(params)}"
                # Changed from networkidle to domcontentloaded because LinkedIn tracking scripts prevent networkidle
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                for card in soup.find_all('div', class_='base-card')[:50]:
                    title_el = card.find('h3', class_='base-search-card__title')
                    company_el = card.find('h4', class_='base-search-card__subtitle')
                    loc_el = card.find('span', class_='job-search-card__location')
                    link_el = card.find('a', class_='base-card__full-link')
                    raw_url = link_el['href'] if link_el else ""
                    clean_url = re.sub(r'https://[a-z]{2}\.linkedin\.com', 'https://www.linkedin.com', raw_url)
                    if title_el and company_el:
                        jobs.append({
                            "title": title_el.text.strip(),
                            "company": company_el.text.strip(),
                            "location": loc_el.text.strip() if loc_el else location,
                            "url": clean_url,
                            "description": "Scraped via Playwright.",
                            "source": "Playwright/LinkedIn"
                        })
                browser.close()
        except Exception as e:
            logger.error(f"Playwright failed: {e}")
        logger.info(f"Playwright [LinkedIn]: {len(jobs)} results")
        return jobs

# ─── HackerNews Scraper ────────────────────────────────────────────────────────
class HackerNewsScraper(BaseJobScraper):
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"HackerNews: '{keywords}'")
        jobs = []
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(keywords)}&tags=story"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for hit in res.json().get('hits', [])[:20]:
                    jobs.append({
                        "title": str(hit.get("title", "") or ""),
                        "company": "HackerNews Startup",
                        "location": "Remote",
                        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                        "description": "HackerNews Job Posting",
                        "source": "HackerNews"
                    })
        except Exception as e:
            logger.error(f"HackerNews failed: {e}")
        return jobs

# ─── RSS Scraper ───────────────────────────────────────────────────────────────
class RSSJobScraper(BaseJobScraper):
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        jobs = []
        feeds = [
            "https://weworkremotely.com/categories/remote-programming-jobs.rss",
            "https://remoteok.com/jobs.rss"
        ]
        kw_words = keywords.lower().split()
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:30]:
                    if not kw_words or any(w in entry.title.lower() for w in kw_words):
                        jobs.append({
                            "title": str(entry.title or ""),
                            "company": "RemoteOK/WWR",
                            "location": "Remote",
                            "url": str(entry.link or ""),
                            "description": str(getattr(entry, 'description', ""))[:300],
                            "source": "RSS Feed"
                        })
            except Exception as e:
                logger.error(f"RSS failed: {e}")
        return jobs

# ─── YCombinator Scraper ────────────────────────────────────────────────────────
class YCScraper(BaseJobScraper):
    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"YC API: '{keywords}'")
        jobs = []
        try:
            import requests
            import json
            from bs4 import BeautifulSoup
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # 1. Fetch meta.json to find recent batches
            res = requests.get("https://raw.githubusercontent.com/yc-oss/api/main/meta.json", timeout=10)
            if res.status_code != 200:
                logger.error("Failed to fetch YC meta.json")
                return jobs
            
            meta = res.json()
            # Sort batches by roughly recency (e.g. S24, W24, S23) or just grab all. 
            # Given that YC API is just static files, fetching 20 batches is incredibly fast.
            # We'll grab the 20 most recently added (or largest ones). Let's just grab the 20 biggest for safety, 
            # or all batches if there aren't many. Actually, 50 batches is just 50 concurrent GETs.
            batch_urls = [b.get("api") for b in meta.get("batches", {}).values() if b.get("api")]
            
            hiring_companies = []
            
            def fetch_batch(url):
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        return r.json()
                except:
                    pass
                return []

            # 2. Concurrently fetch batches to find hiring companies
            # Use top 30 batches to save time (mostly recent/active companies)
            top_urls = list(reversed(list(meta.get("batches", {}).values())))[:30]
            top_batch_urls = [b.get("api") for b in top_urls if b.get("api")]

            all_companies = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(fetch_batch, url): url for url in top_batch_urls}
                for future in as_completed(futures):
                    all_companies.extend(future.result())

            kw_lower = keywords.lower()
            
            # 3. Filter for hiring companies matching keyword
            # Extract significant words from the keyword to avoid overly strict substring matches
            kw_words = [w for w in kw_lower.split() if len(w) > 2 and w not in ('intern', 'developer', 'engineer', 'specialist', 'manager', 'lead', 'senior', 'junior', 'remote')]
            
            for c in all_companies:
                if not c.get("isHiring"):
                    continue
                
                text = f" {c.get('name', '')} {c.get('one_liner', '')} {c.get('long_description', '')} {' '.join(c.get('tags', []))} ".lower()
                
                matched = False
                if not kw_words and 'intern' not in kw_lower:
                    # No significant keywords, just take all and we'll cap later
                    matched = True
                else:
                    for w in kw_words:
                        if w in text:
                            matched = True
                            break
                    # Special short acronyms
                    for acr in [' ai ', ' ml ', ' llm ', ' rag ']:
                        if acr in f" {kw_lower} " and acr in text:
                            matched = True
                            break
                    # If keyword was just "intern", just match companies with "intern" in their text or just take them
                    if 'intern' in kw_lower and ' intern' in text:
                        matched = True
                
                if matched:
                    hiring_companies.append(c)

            logger.info(f"YC API found {len(hiring_companies)} hiring companies matching '{keywords}'")
            
            # 4. Fetch the jobs pages for matching companies
            def fetch_company_jobs(company):
                company_jobs = []
                slug = company.get('slug')
                if not slug: return company_jobs
                
                try:
                    jobs_url = f"https://www.ycombinator.com/companies/{slug}/jobs"
                    r = requests.get(jobs_url, timeout=10)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, 'html.parser')
                        data_div = soup.find('div', {'data-page': True})
                        if data_div:
                            data = json.loads(data_div['data-page'])
                            postings = data.get('props', {}).get('jobPostings', [])
                            for p in postings:
                                # Extra filter: does the specific job match the location and keyword?
                                job_title = p.get('title', '').lower()
                                job_desc = p.get('description', '').lower() if p.get('description') else ''
                                job_loc = p.get('location', '').lower()
                                
                                if location:
                                    loc_lower = location.lower()
                                    # If the job is explicitly remote, it might be global, so we keep it.
                                    # Otherwise, it MUST contain the requested location.
                                    if loc_lower not in job_loc and "remote" not in job_loc:
                                        continue
                                
                                # We already matched the company, but let's include all jobs the company has,
                                # since ATS Scorer will filter the irrelevant ones anyway.
                                company_jobs.append({
                                    "title": p.get("title", ""),
                                    "company": company.get("name", "YC Startup"),
                                    "location": p.get("location", "Remote"),
                                    "url": p.get("applyUrl") or jobs_url,
                                    "description": job_desc[:1000],
                                    "source": "YCombinator"
                                })
                except Exception as e:
                    logger.debug(f"Failed to fetch YC jobs for {slug}: {e}")
                return company_jobs

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(fetch_company_jobs, c): c for c in hiring_companies[:30]} # Cap at 30 to avoid rate limits
                for future in as_completed(futures):
                    jobs.extend(future.result())
        except Exception as e:
            logger.error(f"YC failed: {e}")
        return jobs

# ─── SearxNG + Crawl4AI Scraper ───────────────────────────────────────────────
class SearxNGCrawl4aiScraper(BaseJobScraper):
    """
    Phase 1: SearxNG fires targeted queries against major job boards.
    Phase 2: Crawl4AI visits the actual job board pages and extracts listings.
    Phase 3: LLM parses the raw markdown into structured job dicts.
    """

    def _searxng_query(self, query: str) -> List[str]:
        """Returns a list of unique URLs from SearxNG for a given query."""
        try:
            params = {"q": query, "format": "json"}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get("http://localhost:8080/search", params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                return [r.get("url", "") for r in res.json().get("results", []) if r.get("url")]
        except Exception as e:
            logger.error(f"SearxNG query failed: {e}")
        return []

    # Login wall phrases — if page starts with these, skip to middle content
    LOGIN_SIGNALS = ["login with google", "forgot password", "sign in to", "create account", "register now", "login to continue"]

    def _crawl_and_extract(self, urls: List[str], keyword: str, location: str) -> List[Dict]:
        """Crawl URLs and extract job listings using LLM with login wall detection."""
        from crawl4ai import AsyncWebCrawler
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()

        llm = ChatOllama(
            model=os.getenv("MODEL_NAME", "llama3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )

        async def crawl_all(url_list):
            results = []
            async with AsyncWebCrawler(verbose=False) as crawler:
                for u in url_list:
                    try:
                        r = await crawler.arun(url=u, timeout=20)
                        if r and r.markdown and len(r.markdown) > 200:
                            safe_md = r.markdown.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                            results.append((u, safe_md))
                            logger.info(f"Crawl4AI OK: {_safe(u)} ({len(safe_md)} chars)")
                    except Exception as e:
                        logger.error(f"Crawl4AI failed for {_safe(str(u))}: {_safe(str(e))}")
            return results

        crawled = asyncio.run(crawl_all(urls))
        extracted_jobs = []

        for url, content in crawled:
            # Detect login wall — skip first 3000 chars if it's just a login modal
            if any(sig in content[:2000].lower() for sig in self.LOGIN_SIGNALS):
                logger.info(f"Login wall detected, skipping header: {_safe(url)}")
                content = content[3000:]
                if len(content) < 500:
                    continue

            # Scan content in 3 windows: start, middle, end — job listings can be anywhere
            length = len(content)
            chunk = 7000
            if length <= chunk:
                windows = [content]
            else:
                windows = [
                    content[:chunk],
                    content[length//2 - chunk//2: length//2 + chunk//2],
                    content[max(0, length - chunk):]
                ]

            for window in windows:
                if not window.strip():
                    continue
                prompt = f"""You are a job listing extractor. Extract ALL job postings visible in this text scraped from: {url}
Keyword searched: "{keyword}"

Return ONLY a JSON array. Each item: "title", "company", "location", "url", "description", "source".
For url: use the specific job link if visible, else use "{url}".
For source: the site name (e.g. Internshala, Naukri, LinkedIn).
Return [] if no job listings found. No markdown.

{window}
"""
                try:
                    raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                    for mk in ["```json", "```"]:
                        if raw.startswith(mk): raw = raw[len(mk):]
                    if raw.endswith("```"): raw = raw[:-3]
                    si = raw.find('[')
                    ei = raw.rfind(']') + 1
                    if si != -1 and ei > si:
                        parsed = json.loads(raw[si:ei])
                        if isinstance(parsed, list) and parsed:
                            for pj in parsed:
                                if pj.get("title"):
                                    extracted_jobs.append(pj)
                            logger.info(f"Extracted {len(parsed)} jobs from window of {_safe(url)}")
                            break  # Found jobs in this window, move to next URL
                except Exception as e:
                    logger.error(f"LLM extraction failed: {_safe(str(e))}")

        return extracted_jobs

    def search(self, keywords: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        logger.info(f"SearxNG+Crawl4AI: '{keywords}' in '{location}'")
        all_urls = []
        seen_urls = set()
        snippet_jobs = []  # Fallback: SearxNG result snippets

        loc_str = f" {location}" if location else ""
        targeted_queries = [
            f'"{keywords}" jobs{loc_str} site:internshala.com',
            f'"{keywords}" jobs{loc_str} site:naukri.com',
            f'"{keywords}" jobs{loc_str} site:linkedin.com',
            f'"{keywords}" jobs{loc_str} site:glassdoor.co.in',
            f'"{keywords}" jobs{loc_str} site:wellfound.com',
            f'"{keywords}" jobs{loc_str} site:instahyre.com OR site:foundit.in OR site:unstop.com',
            f'"{keywords}" jobs{loc_str}',
        ]

        for query in targeted_queries:
            try:
                params = {"q": query, "format": "json"}
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                res = requests.get("http://localhost:8080/search", params=params, headers=headers, timeout=10)
                if res.status_code == 200:
                    for r in res.json().get("results", [])[:4]:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_urls.append(url)
                        # Save snippet as fallback
                        if r.get("title") and r.get("url"):
                            snippet_jobs.append({
                                "title": r.get("title", ""),
                                "company": "Web Result",
                                "location": location,
                                "url": r.get("url", ""),
                                "description": r.get("content", "")[:300],
                                "source": "SearxNG"
                            })
            except Exception as e:
                logger.error(f"SearxNG query failed: {_safe(str(e))}")

        logger.info(f"SearxNG: {len(all_urls)} URLs, {len(snippet_jobs)} snippets")

        if not all_urls:
            return snippet_jobs

        extracted = self._crawl_and_extract(all_urls[:12], keywords, location)
        logger.info(f"SearxNG+Crawl4AI: {len(extracted)} extracted, {len(snippet_jobs)} snippets")
        # Return extracted if we got something, otherwise fall back to raw snippets
        return extracted if extracted else snippet_jobs

# ─── Job Aggregator (for MCP server / legacy) ─────────────────────────────────
class JobAggregator:
    def search_all(self, keywords: str, location: str) -> List[Dict[str, Any]]:
        scrapers = [
            LinkedInPlaywrightScraper(),
            JobSpyScraper(site_name="indeed", country="india"),
            JobSpyScraper(site_name="linkedin"),
            HackerNewsScraper(),
            RSSJobScraper(),
            YCScraper(),
            SearxNGCrawl4aiScraper()
        ]
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_jobs = []
        with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
            future_to_scraper = {executor.submit(scraper.search, keywords, location): scraper for scraper in scrapers}
            for future in as_completed(future_to_scraper):
                scraper = future_to_scraper[future]
                try:
                    all_jobs.extend(future.result())
                except Exception as e:
                    logger.error(f"{scraper.__class__.__name__} failed: {e}")

        seen, deduped = set(), []
        for job in all_jobs:
            key = f"{str(job.get('title','')).lower()}|{str(job.get('company','')).lower()}"
            if key not in seen and key != "|":
                seen.add(key)
                deduped.append(job)
        logger.info(f"Aggregator: {len(deduped)} unique jobs total")
        return deduped
