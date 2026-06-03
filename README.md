# Job Hunt AI Agent

Job Hunt AI Agent is an advanced, privacy-first AI job-matching assistant that actively searches, scrapes, and aggregates software engineering and tech jobs tailored precisely to your resume.

Using **cloud-hosted models by Ollama** (via the LangChain ChatOllama interface), modern web scraping (JobSpy, Playwright), and dynamic tool-calling architectures (Model Context Protocol / MCP), this tool serves as your highly personalized, intelligent employment recruiter.

---

## 🌟 Key Features

### 1. **Cloud-Hosted Ollama AI Processing**
By utilizing cloud-hosted Ollama models (configurable via the exposed API URL in the `.env` file), the system leverages powerful off-site LLMs for complex reasoning and data extraction without requiring massive local GPU resources. The AI reads your resume, extracts your exact skills and experience level, and then strictly filters raw job feeds so you only see roles you are truly qualified for.

### 2. **Job Aggregation Engine**
The backend utilizes a multi-pronged approach to find jobs across the web:
* **JobSpy Scraper:** A powerful scraping library that pulls raw postings simultaneously from LinkedIn & Indeed.
* **Playwright Scraper:** Headless browser automation that digs deep into LinkedIn's live job search feeds to bypass basic API limitations.
* **MCP (Model Context Protocol) Servers [Beta]:** 
  * **DuckDuckGo Open Web Search:** Scours the open web for obscure job postings or company-specific hiring pages.
  * **HackerNews Firebase API:** Taps directly into the YCombinator "Who is Hiring" threads and startup job postings.
  * **RSS Job Feeds (RemoteOK & WeWorkRemotely):** Parses XML feeds to instantly pull the latest remote programming and design jobs.

### 3. **AI Post-Processing & Deduplication**
The system doesn't just dump 100 links at you. First, it uses strict deduplication logic (matching lowercase title/company) to ensure you don't see the same job three times. Second, it uses the cloud LLM to actively filter out jobs that require 5+ years of experience if you are a student looking for internships.

### 4. **Modern UI & GitHub-Flavored Markdown**
The frontend is a beautiful, dark-mode React application powered by Vite and Tailwind CSS v4. It features:
* **Dynamic Job Cards:** Clickable, elegantly styled UI cards for every job found.
* **Prose Markdown Rendering:** The AI's analytical responses are rendered using `react-markdown` and `@tailwindcss/typography`, providing gorgeous GitHub-style tables, lists, and bold text.
* **PDF Resume Uploading:** Easily upload your PDF resume directly via the UI, powered by `pdfplumber` on the backend.

---

## 🚀 Step-by-Step Installation & Setup Guide

Follow these exact steps to clone the repository, install all dependencies, and run the Job Hunt AI Agent on your local Windows machine.

### Prerequisites
Before you begin, ensure you have the following installed on your machine:
* [Python 3.11+](https://www.python.org/downloads/)
* [Node.js (v18+)](https://nodejs.org/)
* Git
* Access to a **cloud-hosted Ollama API URL**.

### Step 1: Clone the Repository
Open your terminal (PowerShell or Command Prompt) and run:
```bash
git clone https://github.com/avish006/job-hunt-agent.git
cd job-hunt-agent
```

### Step 2: Set Up the Python Backend
The backend requires a virtual environment to manage its scraping and AI dependencies safely.

1. **Navigate to the backend folder:**
   ```bash
   cd backend
   ```
2. **Create a virtual environment:**
   ```bash
   python -m venv venv2
   ```
3. **Activate the virtual environment (Windows PowerShell):**
   ```powershell
   .\venv2\Scripts\Activate.ps1
   ```
4. **Install dependencies from `requirements.txt`:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Install Playwright Browsers:**
   Since the app uses Playwright for scraping, you must install the headless browsers:
   ```bash
   playwright install chromium
   ```
6. **Windows Specific: PyWin32 Post-Install:**
   The MCP server requires COM objects. Run the post-install script to ensure `pywintypes` works correctly:
   ```bash
   python .\venv2\Scripts\pywin32_postinstall.py -install
   ```
7. **Configure your Environment (.env):**
   Create a `.env` file in the `backend/` directory and configure your cloud Ollama endpoint:
   ```env
   MODEL_PROVIDER=ollama
   MODEL_NAME=gpt-oss:120b-cloud #Change this with any other ollama Cloud LLM ID.
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### Step 3: Set Up the React Frontend
Open a **new, separate terminal window** (keep the backend terminal open) for the frontend.

1. **Navigate to the frontend folder:**
   ```bash
   cd frontend
   ```
2. **Install Node modules:**
   ```bash
   npm install
   ```

### Step 4: Run the Application

You need to run both the backend server and the frontend development server simultaneously.

**In the Backend Terminal (make sure `venv2` is activated):**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**In the Frontend Terminal:**
```bash
npm run dev
```

### Step 5: Start Hunting!
1. Open your browser and navigate to the local URL provided by Vite (usually `http://localhost:5173`).
2. **Upload your Resume:** Click the "Upload PDF..." button in the left sidebar and select your resume.
3. **Search for Jobs:** Type a prompt into the chat box like: *"Find me junior React developer roles. Ignore senior roles."*
4. **Review Results:** The AI will process your request, trigger the scrapers in the background, actively filter the results against your resume, and present beautifully formatted markdown analysis alongside interactive Job Cards!

---

## 🛠️ Tech Stack
* **Backend:** Python, FastAPI, Uvicorn, LangChain, Ollama, JobSpy, Playwright, BeautifulSoup4, Feedparser, DuckDuckGo Search, MCP (Model Context Protocol).
* **Frontend:** TypeScript, React, Vite, Tailwind CSS v4, React-Markdown, Remark-GFM.
* **Data Processing:** Pandas, PDFPlumber.

---

## ⚠️ Troubleshooting & Known Issues
* **Known MCP Connectivity Issues (Beta):** The MCP (Model Context Protocol) subsystem currently has known execution issues under Windows `stdio` pipes, which can cause the servers to fail silently or throw `pywintypes` errors during the async event loop setup. This is actively being investigated. 
* **`ValueError: Out of range float values are not JSON compliant`**: This is mitigated by our rigorous backend sanitization, but if you heavily modify `JobSpyScraper`, ensure any new pandas columns are cast to `str()` or `fillna("")` is applied before returning the dictionary to FastAPI.

Happy Hunting! 🚀
