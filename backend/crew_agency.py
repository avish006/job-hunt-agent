import os
import json
import logging
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

logger = logging.getLogger(__name__)

os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm_string = f"ollama/{os.getenv('MODEL_NAME', 'llama3')}"

GLOBAL_SCRAPED_JOBS = []

# ─── Tools ─────────────────────────────────────────────────────────────────────

@tool("Search JobSpy Indeed and LinkedIn")
def tool_search_jobspy(keyword: str, location: str) -> str:
    """Searches Indeed and LinkedIn via JobSpy for ONE specific keyword.
    Always call this first for each keyword. Returns a JSON list."""
    from scraper import JobSpyScraper
    jobs = []
    country = "india" if any(w in location.lower() for w in [
        "india", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "remote"
    ]) else "usa"
    for site, c in [("indeed", country), ("linkedin", "usa")]:
        try:
            results = JobSpyScraper(site_name=site, country=c).search(keyword, location)
            jobs.extend(results)
            logger.info(f"JobSpy [{site}] '{keyword}': {len(results)} results")
        except Exception as e:
            logger.error(f"JobSpy [{site}] failed: {e}")
    GLOBAL_SCRAPED_JOBS.extend(jobs)
    return f"Success: {len(jobs)} jobs found and recorded."


@tool("Search LinkedIn via Playwright Browser")
def tool_search_playwright(keyword: str, location: str) -> str:
    """Searches LinkedIn live via headless browser for ONE keyword.
    Use after JobSpy to supplement results. Returns a JSON list."""
    from scraper import LinkedInPlaywrightScraper
    jobs = []
    try:
        jobs.extend(LinkedInPlaywrightScraper().search(keyword, location))
        logger.info(f"Playwright '{keyword}': {len(jobs)} results")
    except Exception as e:
        logger.error(f"Playwright failed: {e}")
    GLOBAL_SCRAPED_JOBS.extend(jobs)
    return f"Success: {len(jobs)} jobs found and recorded."


@tool("Deep Search SearxNG and Crawl4AI")
def tool_deep_search_searxng(keyword: str, location: str) -> str:
    """Searches Naukri, Internshala, Glassdoor, Wellfound, Instahyre and more
    using SearxNG targeted queries + Crawl4AI extraction for ONE keyword.
    Returns a JSON list."""
    from scraper import SearxNGCrawl4aiScraper
    try:
        jobs = SearxNGCrawl4aiScraper().search(keyword, location)
        logger.info(f"SearxNG+Crawl4AI '{keyword}': {len(jobs)} results")
        GLOBAL_SCRAPED_JOBS.extend(jobs)
        return f"Success: {len(jobs)} jobs found and recorded."
    except Exception as e:
        logger.error(f"SearxNG+Crawl4AI failed: {e}")
        return "Failed to scrape jobs."


@tool("Search RSS feeds for Remote Jobs")
def tool_search_rss(keyword: str, location: str) -> str:
    """Searches remote job RSS feeds (WeWorkRemotely, RemoteOK) for ONE keyword.
    Returns a JSON list."""
    from scraper import RSSJobScraper
    try:
        jobs = RSSJobScraper().search(keyword, location)
        logger.info(f"RSS '{keyword}': {len(jobs)} results")
        GLOBAL_SCRAPED_JOBS.extend(jobs)
        return f"Success: {len(jobs)} jobs found and recorded."
    except Exception as e:
        logger.error(f"RSS failed: {e}")
        return "Failed to scrape jobs."

@tool("Search YCombinator for Startups")
def tool_search_yc(keyword: str, location: str) -> str:
    """Searches YCombinator WorkAtAStartup for ONE keyword.
    Returns a JSON list."""
    from scraper import YCScraper
    try:
        jobs = YCScraper().search(keyword, location)
        logger.info(f"YC '{keyword}': {len(jobs)} results")
        GLOBAL_SCRAPED_JOBS.extend(jobs)
        return f"Success: {len(jobs)} jobs found and recorded."
    except Exception as e:
        logger.error(f"YC failed: {e}")
        return "Failed to scrape jobs."

# ─── Deploy Agency ─────────────────────────────────────────────────────────────

def deploy_job_hunt_agency(
    keywords_list: list,
    location: str,
    resume_text: str,
    user_prompt: str = ""
) -> tuple:
    """
    Deploys the Sourcer crew to scrape all boards, then runs the ATS scorer.
    Returns: (summary_text: str, scored_jobs: list)
    """
    GLOBAL_SCRAPED_JOBS.clear()
    keywords_str = ", ".join(keywords_list)

    sourcer = Agent(
        role="Senior Technical Sourcing Recruiter",
        goal=f"Find as many real job postings as possible for: {keywords_str}",
        backstory=(
            "You are an aggressive headhunter who NEVER makes up job listings. "
            "You MUST call each search tool separately for EACH keyword. "
            "Process: for EACH keyword in the list, call JobSpy, Playwright, SearxNG, RSS, and YC tools. "
            f"Keywords to search one-by-one: {keywords_str}. Location: {location}. "
            "Compile ALL results into one master JSON list."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[
            tool_search_jobspy, 
            tool_search_playwright, 
            tool_deep_search_searxng,
            tool_search_rss,
            tool_search_yc
        ],
        llm=llm_string
    )

    source_task = Task(
        description=(
            f"Search for jobs using these keywords (search each SEPARATELY):\n"
            f"Keywords: {keywords_str}\n"
            f"Location: {location}\n\n"
            f"For EACH keyword:\n"
            f"1. Call 'Search JobSpy Indeed and LinkedIn' with that keyword\n"
            f"2. Call 'Search LinkedIn via Playwright Browser' with that keyword\n"
            f"3. Call 'Deep Search SearxNG and Crawl4AI' with that keyword\n"
            f"4. Call 'Search RSS feeds for Remote Jobs' with that keyword\n"
            f"5. Call 'Search YCombinator for Startups' with that keyword\n\n"
            f"Compile ALL results from all tools into one master list. "
            f"Remove obvious duplicates (same title + company). Return as JSON array."
        ),
        expected_output=(
            "A JSON array of ALL scraped jobs. Each item: "
            "'title', 'company', 'location', 'url', 'description', 'source'."
        ),
        agent=sourcer
    )

    crew = Crew(
        agents=[sourcer],
        tasks=[source_task],
        process=Process.sequential,
        verbose=True
    )

    # ── Force execution of deterministic scrapers to bypass LLM laziness ────
    from concurrent.futures import ThreadPoolExecutor
    logger.info("Programmatically executing YC and RSS scrapers to ensure coverage...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        for kw in keywords_list:
            executor.submit(tool_search_yc.func, kw, location)
            executor.submit(tool_search_rss.func, kw, location)

    raw_output = str(crew.kickoff())

    # ── Bypass LLM output and use directly accumulated jobs ─────────────────
    seen = set()
    raw_jobs = []
    for job in GLOBAL_SCRAPED_JOBS:
        if not isinstance(job, dict): continue
        key = f"{str(job.get('title','')).lower()}|{str(job.get('company','')).lower()}"
        if key not in seen and key != "|":
            seen.add(key)
            raw_jobs.append(job)
    logger.info(f"Sourcer returned {len(raw_jobs)} unique raw jobs from direct tool capture")

    if not raw_jobs:
        return "The sourcing agency returned no jobs. Try different keywords or check scraper logs.", [], []

    # ── ATS + Semantic Scoring ───────────────────────────────────────────────
    from ats_scorer import score_all_jobs
    scored_jobs = score_all_jobs(resume_text, raw_jobs)
    logger.info(f"ATS Scorer: {len(scored_jobs)} jobs scored and ranked")

    # ── Build summary ────────────────────────────────────────────────────────
    summary = (
        f"**{len(scored_jobs)} total jobs** scraped and scored.\n"
        f"- All jobs are sorted by match score — use the sliders to filter.\n"
    )

    return summary, scored_jobs, raw_jobs
