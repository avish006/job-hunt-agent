from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="Job Hunt AI Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "Job Hunt AI Agent API is running."}

# Global state for the local app
USER_CONTEXT = {
    "resume_text": ""
}

@app.post("/api/chat")
def chat(request: ChatRequest):
    from agent import run_agent
    try:
        reply, jobs_list = run_agent(request.message, USER_CONTEXT["resume_text"])
        return {"reply": reply, "jobs": jobs_list}
    except Exception as e:
        return {"reply": f"Agent encountered an error: {str(e)}"}

@app.post("/api/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    import pdfplumber
    from io import BytesIO
    content = await file.read()
    
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        # Save to global context
        USER_CONTEXT["resume_text"] = text
        
        return {"filename": file.filename, "status": "Parsed successfully", "text_length": len(text), "preview": text[:200]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
