# Agentic AI Job Hunt Platform ??

An autonomous, agentic job hunting pipeline that finds, parses, and semantically scores job postings against your resume.

## ?? How It Works Internally

This project is built using a modern Agentic AI architecture designed to simulate a professional recruitment sourcer and an ATS scoring system.

1. **User Prompt & Resume Parsing**: The user uploads their resume (PDF) and provides a natural language prompt (e.g., *"Find me suitable AI internships in India"*). The backend uses **PyMuPDF** to extract the resume text.
2. **Agent Orchestrator (CrewAI & Ollama)**: The system feeds your prompt to a local **Llama 3** model using **CrewAI**. The LLM acts as an autonomous agent, analyzing your prompt to generate highly specific search keywords and targeted locations.
3. **Multi-Source Scraping**: The agent programmatically triggers a fleet of specialized scrapers simultaneously:
   - **JobSpy**: Aggregates standard listings from Indeed and LinkedIn.
   - **YC API Scraper**: Connects directly to the YCombinator public API and startup job boards (ycombinator.com/companies/<slug>/jobs) to find high-quality stealth and early-stage startup roles.
   - **SearxNG + Crawl4AI**: A self-hosted metasearch engine (SearxNG) locates jobs on niche platforms (like Internshala, Wellfound, Naukri). **Crawl4AI** then asynchronously visits those URLs, bypasses login walls, extracts the raw Markdown, and uses an LLM to parse the data into structured JSON.
   - **RSS Scraper**: Scrapes remote job boards via public XML feeds.
4. **ATS Semantic Scoring**: Once hundreds of raw jobs are aggregated, the **SentenceTransformers** model semantically compares your resume against every single job description. It generates a strict "ATS Match Score", dropping irrelevant listings and sorting the rest.
5. **Frontend UI**: A sleek, modern **React + Vite** interface displays the curated job cards. You can dynamically filter jobs using an ATS score slider.

---

## ??? Blind Installation Guide

Follow these exact steps if you want to run this project from scratch. You do not need to know how the code works to get it running!

### Prerequisites
Before you begin, ensure you have installed:
- **Python 3.10+**
- **Node.js** (v18 or higher)
- **Docker** and **Docker Desktop** (Required for SearxNG)
- **Ollama** (Required for the local AI models. Download from [ollama.com](https://ollama.com/))

### Step 1: Clone the Repository
Open your terminal and run:
\\\ash
git clone https://github.com/avish006/job-hunt-agent.git
cd job-hunt-agent
\\\

### Step 2: Setup Local AI (Ollama)
Open your terminal and download the required AI model:
\\\ash
ollama run llama3
\\\
*(You can close this terminal once it says "success" and gives you a prompt).*

### Step 3: Setup the Metasearch Engine (SearxNG)
The scraper relies on a local instance of SearxNG to bypass rate limits.
1. Make sure **Docker Desktop** is open and running on your computer.
2. In a terminal, navigate to the SearxNG config folder and start it:
\\\ash
cd searxng_config
docker-compose up -d
\\\
3. Verify it's running by going to \http://localhost:8080\ in your browser.

### Step 4: Setup the Python Backend
Open a new terminal in the \job-hunt-agent/backend\ folder.
1. Create a virtual environment:
\\\ash
python -m venv venv
\\\
2. Activate the virtual environment:
   - **Windows:** \.\venv\Scripts\activate\
   - **Mac/Linux:** \source venv/bin/activate\
3. Install all the required packages:
\\\ash
pip install -r requirements.txt
playwright install
\\\
4. Start the backend server:
\\\ash
uvicorn main:app --reload
\\\
*(Leave this terminal running!)*

### Step 5: Setup the React Frontend
Open a new terminal in the \job-hunt-agent/frontend\ folder.
1. Install the Node modules:
\\\ash
npm install
\\\
2. Start the frontend server:
\\\ash
npm run dev
\\\

### Step 6: Start Job Hunting!
Go to \http://localhost:5173\ in your web browser. Upload your resume, type your prompt, and let the agent find your next job!
