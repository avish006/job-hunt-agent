"""
ATS Scoring Engine
------------------
Two independent scoring signals per job:

1. ATS Score (Keyword-based)
   - Extracts skills/tools/roles from the resume
   - Counts how many appear in the job title + description
   - Fast, deterministic, mirrors real recruiter ATS systems

2. Semantic Score (TF-IDF Cosine Similarity)
   - Fits a shared TF-IDF matrix on resume + all job descriptions
   - Computes cosine similarity between resume vector and each job vector
   - Captures conceptual overlap beyond exact keyword matching

Combined Score = 0.5 * ATS + 0.5 * Semantic
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ─── Master Skills & Keywords List ────────────────────────────────────────────
# Broad enough to cover any domain. The ATS scorer only counts skills
# that ALSO appear in the resume, so irrelevant domains auto-score low.
SKILLS_VOCAB = [
    # Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby",
    "php", "swift", "kotlin", "scala", "r", "matlab", "julia", "bash", "shell",
    # Web & Frontend
    "react", "next.js", "vue", "angular", "html", "css", "tailwind", "bootstrap",
    "redux", "graphql", "rest api", "websocket", "webpack", "vite", "node.js",
    "express", "fastapi", "flask", "django", "spring boot", "rails",
    # Databases
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "dynamodb", "firebase", "supabase", "vector database", "pinecone", "weaviate",
    "chromadb", "faiss", "lancedb",
    # ML / AI / LLM
    "machine learning", "deep learning", "neural network", "nlp", "computer vision",
    "reinforcement learning", "generative ai", "llm", "large language model",
    "transformer", "bert", "gpt", "llama", "mistral", "gemini", "claude",
    "langchain", "langgraph", "llamaindex", "autogen", "crewai",
    "rag", "retrieval augmented generation", "fine-tuning", "lora", "qlora",
    "embeddings", "vector search", "semantic search", "prompt engineering",
    "hugging face", "diffusion model", "stable diffusion",
    # ML Frameworks
    "pytorch", "tensorflow", "keras", "scikit-learn", "xgboost", "lightgbm",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    # MLOps / DevOps / Cloud
    "docker", "kubernetes", "aws", "azure", "gcp", "google cloud", "ec2", "s3",
    "lambda", "ci/cd", "github actions", "jenkins", "terraform", "ansible",
    "mlflow", "wandb", "airflow", "kafka", "spark", "hadoop",
    # Data Engineering
    "data pipeline", "etl", "data warehouse", "dbt", "snowflake", "bigquery",
    "data lake", "stream processing", "batch processing",
    # Finance / Business (for non-tech resumes)
    "financial analysis", "accounting", "excel", "power bi", "tableau", "erp",
    "sap", "salesforce", "crm", "investment", "valuation", "equity", "derivatives",
    # Healthcare / Science
    "clinical", "bioinformatics", "genomics", "matlab", "r", "spss", "stata",
    # Generic soft / role keywords
    "intern", "internship", "fresher", "entry level", "junior", "senior",
    "full stack", "backend", "frontend", "data science", "research",
    "product management", "ui/ux", "mobile", "android", "ios",
]

def _normalize(text: str) -> str:
    """Lowercase, remove punctuation except hyphens/dots."""
    return re.sub(r'[^\w\s\-\.]', ' ', text.lower())

# Map abbreviations/synonyms to canonical terms in SKILLS_VOCAB
SYNONYMS = {
    "ai": "artificial intelligence",
    "artificial intelligence": "ai", # Match both ways if needed, but vocab doesn't have "ai", let's add it to vocab or just map
    "ml": "machine learning",
    "genai": "generative ai",
    "nlp": "natural language processing",
    "llm": "large language model",
    "llms": "large language model",
    "dl": "deep learning",
    "rl": "reinforcement learning",
    "ui": "ui/ux",
    "ux": "ui/ux",
    "aws": "amazon web services",
    "gcp": "google cloud",
    "k8s": "kubernetes",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "nextjs": "next.js",
    "cv": "computer vision",
    "ds": "data science",
}

def _extract_skills(text: str) -> set:
    norm = _normalize(text)
    found = set()
    
    # 1. Direct match with SKILLS_VOCAB
    for skill in SKILLS_VOCAB:
        if re.search(r'\b' + re.escape(skill) + r'\b', norm):
            found.add(skill)
            
    # 2. Match synonyms and add canonical form
    for syn, canonical in SYNONYMS.items():
        if re.search(r'\b' + re.escape(syn) + r'\b', norm):
            found.add(canonical)
            
    return found

def ats_score(resume_text: str, job_text: str) -> float:
    """
    ATS Score: what % of the candidate's skills appear in the job description.
    Score 0–100.
    """
    resume_skills = _extract_skills(resume_text)
    if not resume_skills:
        return 40.0  # Neutral if resume has no parseable skills
    job_skills = _extract_skills(job_text)
    matched = resume_skills & job_skills
    score = (len(matched) / len(resume_skills)) * 100
    return min(round(score, 1), 100.0)


def semantic_score_bulk(resume_text: str, job_texts: List[str]) -> List[float]:
    """
    Semantic Score: TF-IDF cosine similarity between resume and each job.
    Computed in bulk for efficiency. Returns list of scores 0–100.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        docs = [resume_text] + job_texts
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform(docs)
        resume_vec = tfidf_matrix[0:1]
        job_vecs = tfidf_matrix[1:]
        similarities = cosine_similarity(resume_vec, job_vecs)[0]
        return [round(float(s) * 100, 1) for s in similarities]
    except Exception as e:
        logger.error(f"Semantic scoring failed: {e}")
        return [0.0] * len(job_texts)


def score_all_jobs(resume_text: str, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score all jobs against the resume.
    Adds 'ats_score', 'semantic_score', 'combined_score', 'matched_skills' to each job.
    Returns all jobs sorted by combined_score descending.
    """
    if not jobs:
        return []

    logger.info(f"ATS Scorer: scoring {len(jobs)} jobs against resume...")

    # Prepare job texts
    job_texts = [
        f"{j.get('title', '')} {j.get('company', '')} {j.get('description', '')}"
        for j in jobs
    ]

    # Compute semantic scores in bulk (one TF-IDF fit for all jobs — fast)
    sem_scores = semantic_score_bulk(resume_text, job_texts)

    # Compute ATS scores individually (keyword matching)
    scored = []
    for i, job in enumerate(jobs):
        jd_text = job_texts[i]

        # ATS keyword score
        a_score = ats_score(resume_text, jd_text)

        # Semantic TF-IDF score
        s_score = sem_scores[i]

        # Combined
        combined = round(0.5 * a_score + 0.5 * s_score, 1)

        # Which skills matched (for tooltip display)
        resume_skills = _extract_skills(resume_text)
        job_skills = _extract_skills(jd_text)
        matched = sorted(list(resume_skills & job_skills))

        job_copy = dict(job)
        job_copy['ats_score'] = a_score
        job_copy['semantic_score'] = s_score
        job_copy['combined_score'] = combined
        job_copy['matched_skills'] = matched[:10]  # top 10 for display
        scored.append(job_copy)

    # Sort by combined score descending
    scored.sort(key=lambda x: x['combined_score'], reverse=True)

    logger.info(f"ATS Scorer: done. Top score={scored[0]['combined_score'] if scored else 0}%")
    return scored
