import os
import json
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Initialize Chat LLM
llm = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL)

def search_jobs_tool(keywords: str, location: str) -> str:
    """Manual tool function to search jobs using all engines."""
    try:
        from scraper import JobAggregator
        aggregator = JobAggregator()
        jobs = aggregator.search_all(keywords=keywords, location=location)
        
        if not jobs:
            return "No jobs found matching your criteria across any engines."
            
        result = f"Found {len(jobs)} unique jobs (Aggregated via Playwright, JobSpy & MCP):\n"
        for i, j in enumerate(jobs):
            result += f"{i+1}. {j['title']} at {j['company']} ({j['location']})\n   Source: {j.get('source', 'Unknown')}\n   URL: {j['url']}\n"
        return result
    except Exception as e:
        return f"Error searching jobs: {str(e)}"

def run_agent(message: str, resume_text: str = "") -> str:
    # 1. Ask the LLM to extract search parameters
    extraction_prompt = f"""You are a job search assistant.
Based on the user's message and their resume, extract the best job search keywords and location.
If the user is not asking to search for jobs, output empty strings.
Output ONLY valid JSON with keys "keywords", "location", "is_search". No other text.

Resume:
{resume_text}

User Message:
{message}

Example Output:
{{"keywords": "Software Engineering Internship", "location": "Remote", "is_search": true}}
"""

    try:
        extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])
        # Parse the JSON response
        try:
            content = extraction_response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            parsed = json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback if it fails to output pure JSON
            parsed = {"is_search": False}

        # 2. If it's a search, execute it
        search_results = ""
        jobs_list = []
        if parsed.get("is_search"):
            kw = parsed.get("keywords", "internship")
            loc = parsed.get("location", "Remote")
            
            from scraper import JobAggregator
            aggregator = JobAggregator()
            jobs_list = aggregator.search_all(keywords=kw, location=loc)
            
            if jobs_list:
                filter_prompt = f"""You are a strict Job Matching Filter.
The user's resume is:
{resume_text}

The user requested: keywords: '{kw}', location: '{loc}'

Here are the raw scraped jobs:
{json.dumps([{"id": i, "title": j["title"], "company": j["company"], "location": j["location"]} for i, j in enumerate(jobs_list)])}

Identify ONLY the jobs that strictly match the user's experience level and location. Ignore jobs that ask for 2+ years of experience if the user is a student looking for internships.
Output a JSON list of the matching job IDs. ONLY output the JSON array (e.g. [0, 2, 5]). If none match, output []. No other text.
"""
                filter_res = llm.invoke([HumanMessage(content=filter_prompt)])
                try:
                    content = filter_res.content.strip()
                    if content.startswith("```json"): content = content[7:]
                    if content.startswith("```"): content = content[3:]
                    if content.endswith("```"): content = content[:-3]
                    valid_ids = json.loads(content.strip())
                    if isinstance(valid_ids, list):
                        jobs_list = [jobs_list[i] for i in valid_ids if i < len(jobs_list)]
                except Exception:
                    pass
            
            if not jobs_list:
                search_results = "No jobs found matching your criteria across any engines."
            else:
                search_results = f"Found {len(jobs_list)} unique jobs (Aggregated via Playwright, JobSpy & MCP):\n"
                for i, j in enumerate(jobs_list):
                    search_results += f"{i+1}. {j['title']} at {j['company']} ({j['location']})\n   Source: {j.get('source', 'Unknown')}\n   URL: {j['url']}\n"

        # 3. Generate final response
        synthesis_prompt = f"""You are an AI Job Hunting Assistant. Your goal is to help the user based on their resume and the search results.

User's Resume:
{resume_text}

User Message: {message}

Job Search Results:
{search_results}

If search results are provided, present a brief summary to the user. Explain why they are a good match based on their resume. DO NOT list the jobs out one by one in text, because they will be displayed as interactive UI cards automatically.
"""
        final_response = llm.invoke([HumanMessage(content=synthesis_prompt)])
        return final_response.content, jobs_list

    except Exception as e:
        return f"The agent encountered an execution error: {str(e)}", []
