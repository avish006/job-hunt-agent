import os
import json
import logging
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = ChatOllama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL)

def run_agent(message: str, resume_text: str = "") -> tuple:
    """
    CEO Agent:
    1. Reads resume + prompt → extracts a LIST of keyword variants (not one combined string)
    2. Deploys CrewAI agency with the keyword list
    3. Returns (reply_text, jobs_list) where jobs_list feeds the frontend job cards
    """
    try:
        # ── Step 1: Extract keyword LIST + location ──────────────────────────
        extraction_prompt = f"""You are a world-class technical recruiter with deep domain expertise across all industries.

Your task: read this candidate's resume and request, identify their PRIMARY DOMAIN, then generate highly specific niche job title keywords within that domain.

CANDIDATE'S REQUEST:
"{message}"

CANDIDATE'S FULL RESUME:
{resume_text}

STEP 1 — Identify the domain:
Read the resume. What is the candidate's PRIMARY domain?
Examples: Generative AI / LLMs, Traditional ML / Data Science, Cybersecurity, Full Stack Web Dev, DevOps / Cloud, Mobile Dev, Blockchain, Marketing / Growth, Finance / Quant, Biotech, etc.

STEP 2 — Generate 5 to 8 Relevant keyword variants WITHIN that domain.
Rules:
- Every keyword must stay within the identified domain. Do NOT generate generic titles like "Software Engineer" or "Tech Intern" — those are too broad.
- Generate SPECIFIC, Relevant titles that a recruiter in that domain would actually post.
- Use the candidate's exact tools, frameworks, and projects to make keywords ultra-specific.
- Each keyword is ONE standalone job title — never combine two roles into one string.
- If the resume shows a student / fresher (no full-time work experience), append "Intern" or "Fresher" to each keyword.

DOMAIN KEYWORD EXAMPLES (for reference only — generate for the actual resume domain):

  Generative AI domain → "LLM Inference Engineer Intern", "RAG Pipeline Developer Intern", "Agentic AI Intern", "Prompt Engineer Intern", "LangChain Developer Intern", "LangGraph Engineer Intern", "Multimodal AI Intern", "AI Alignment Research Intern", "LLM Fine-tuning Intern", "Generative AI Application Intern"

  Cybersecurity domain → "Penetration Testing Intern", "Red Team Intern", "SOC Analyst Intern", "Threat Intelligence Intern", "Malware Analysis Intern", "Cloud Security Intern", "CTF Researcher Intern", "Vulnerability Research Intern"

  Full Stack Web domain → "React Developer Intern", "Next.js Developer Intern", "Node.js Backend Intern", "MERN Stack Intern", "GraphQL Developer Intern", "TypeScript Engineer Intern"

  DevOps / Cloud domain → "Cloud Infrastructure Intern", "Kubernetes Engineer Intern", "Site Reliability Intern", "Platform Engineer Intern", "CI/CD Pipeline Intern"

  Data Science / Analytics domain → "Data Analyst Intern", "Business Intelligence Intern", "SQL Analytics Intern", "Tableau Developer Intern", "Statistical Modeling Intern"

STEP 3 — Extract location from the request. Default to "Remote" if not mentioned.

Return ONLY a raw JSON object. No markdown. Example:
{{"keywords": ["RAG Pipeline Developer Intern", "LangChain Developer Intern", "LLM Fine-tuning Intern", "Agentic AI Intern", "LangGraph Engineer Intern", "Multimodal AI Intern", "Prompt Engineer Intern", "Generative AI Application Intern"], "location": "Remote India"}}
"""
        logger.info("CEO Agent: Extracting keyword list from resume + prompt...")
        res = llm.invoke([HumanMessage(content=extraction_prompt)])
        raw_json = res.content.strip()
        for mk in ["```json", "```"]:
            if raw_json.startswith(mk): raw_json = raw_json[len(mk):]
        if raw_json.endswith("```"): raw_json = raw_json[:-3]

        try:
            parsed = json.loads(raw_json.strip())
            keywords_list = parsed.get("keywords", [message])
            if isinstance(keywords_list, str):
                keywords_list = [keywords_list]
            location = parsed.get("location", "Remote")
        except json.JSONDecodeError:
            logger.warning("CEO Agent: JSON parse failed, using raw message.")
            keywords_list = [message]
            location = "Remote"

        print(f"\n[CEO Agent] 🎯 Keywords: {keywords_list} | Location: '{location}'\n")
        logger.info(f"CEO Agent: keywords={keywords_list}, location='{location}'")

        # ── Step 2: Deploy the CrewAI agency ────────────────────────────────
        from crew_agency import deploy_job_hunt_agency
        markdown_summary, jobs_list, raw_jobs_list = deploy_job_hunt_agency(
            keywords_list=keywords_list,
            location=location,
            resume_text=resume_text,
            user_prompt=message
        )

        # ── Step 3: Build the reply ──────────────────────────────────────────
        keywords_display = ", ".join([f"`{k}`" for k in keywords_list])
        reply = (
            f"### ✅ Job Hunt Complete\n"
            f"**Searched:** {keywords_display} in `{location}`\n"
            f"**Matched jobs:** {len(jobs_list)} relevant postings found\n\n"
            f"{markdown_summary}"
        )

        return reply, jobs_list, raw_jobs_list

    except Exception as e:
        logger.error(f"CEO Agent error: {e}", exc_info=True)
        return f"The CEO agent encountered an execution error: {str(e)}", []
