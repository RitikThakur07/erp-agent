"""
Multi-Agent AI Code Generator
PM Agent → Backend Agent → Frontend Agent → QA Agent
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Multi-Agent Code Generator")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated projects
PROJECTS_DIR = Path("generated_projects")
PROJECTS_DIR.mkdir(exist_ok=True)

# Store conversation history per project (in-memory cache)
conversation_history: dict[str, list] = {}
# Track PM questioning rounds to avoid long back-and-forth
pm_rounds: dict[str, int] = {}

def load_history(project_id: str) -> list:
    """Load conversation history from disk if available."""
    try:
        convo_file = PROJECTS_DIR / project_id / "conversation.json"
        if convo_file.exists():
            return json.loads(convo_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def save_history(project_id: str):
    """Persist conversation history to disk."""
    try:
        project_dir = PROJECTS_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        convo_file = project_dir / "conversation.json"
        convo_file.write_text(json.dumps(conversation_history.get(project_id, []), ensure_ascii=False, indent=2), encoding="utf-8")
        # touch meta for updated time
        meta_file = project_dir / "meta.json"
        meta = {"last_updated": datetime.utcnow().isoformat() + "Z"}
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
    except Exception:
        pass


class ChatMessage(BaseModel):
    message: str
    project_id: str = "default"


@app.get("/")
async def root():
    """Serve the main chat interface"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


async def call_gemini(prompt: str) -> str:
    """Call Gemini API in thread pool"""
    def _sync_call():
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    
    return await asyncio.to_thread(_sync_call)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket for multi-agent workflow"""
    await websocket.accept()
    # Defer project_id until first message; allows client to reconnect to existing project
    project_id: str | None = None
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            client_pid = (data.get("project_id") or "").strip() or None
            # Initialize project context on first message
            if project_id is None:
                project_id = client_pid or f"project_{int(datetime.utcnow().timestamp()*1000)}"
                # Load existing history if any
                conversation_history[project_id] = load_history(project_id)
                pm_rounds[project_id] = pm_rounds.get(project_id, 0)
            # Force build keywords
            lower = (message or "").strip().lower()
            force_build = (
                "__force_build__" in lower
                or lower in {"build now", "start build", "generate now", "start", "/build"}
                or "go ahead" in lower or "ready" in lower
            )
            
            # Add to conversation
            conversation_history[project_id].append({"role": "user", "content": message})
            save_history(project_id)
            
            # PM Agent Chat
            await websocket.send_json({
                "type": "pm_thinking",
                "content": "🤔 PM Agent analyzing requirements..."
            })
            
            pm_prompt = f"""You are a Project Manager AI Agent SPECIALIZED in ERP (Enterprise Resource Planning) systems.

Your ONLY focus: ERP systems like Inventory, Sales, HR, Finance, Manufacturing, CRM, Warehouse, Orders, etc.

Conversation so far:
{format_conversation(conversation_history[project_id])}

Current user message: "{message}"

FIRST: Check if this is an ERP-related request.

ERP systems include:
- Inventory Management
- Sales & Order Management
- HR & Payroll
- Finance & Accounting
- Manufacturing & Production
- Warehouse Management
- Customer Relationship Management (CRM)
- Supply Chain Management
- Purchase Management
- Asset Management
- Project Management
- Reporting & Analytics for business

NON-ERP examples (REJECT these):
- Todo apps, calculators, timers
- Gaming apps, entertainment
- Social media, chat apps
- Generic landing pages, portfolios
- Weather apps, news readers
- Simple utilities

YOUR RESPONSE:

1. If request is NOT ERP-related, respond EXACTLY:
   "I apologize, but our team specializes in ERP (Enterprise Resource Planning) systems. We help build business management applications like Inventory, Sales, HR, Finance, Manufacturing, etc. 
   
   Could you describe an ERP system you'd like to build? For example:
   - Inventory management system
   - Sales order processing
   - HR management system
   - Warehouse management"

2. If request IS ERP-related but needs more details, ask at most one round with 2-3 concise questions about:
   - Business modules needed
   - User roles and permissions
   - Data entities to manage
   - Key workflows
   - Reporting needs

3. If requirements are COMPLETE for an ERP system OR the user says to start (e.g., "build now", "start", "go ahead"), respond:
    "Thank you! I have all the requirements. Give me a moment to coordinate with my development team..." [READY]

Important constraints:
- Keep the questioning to a single round. After one back-and-forth, proceed with [READY].

Be professional and guide users toward ERP solutions."""

            if force_build:
                pm_response = "Thank you! I have all the requirements. Give me a moment to coordinate with my development team... [READY]"
            else:
                pm_response = await call_gemini(pm_prompt)
            
            # Add PM response to history
            conversation_history[project_id].append({"role": "assistant", "content": pm_response})
            save_history(project_id)
            
            # Send PM response
            await websocket.send_json({
                "type": "pm_response",
                "content": pm_response
            })
            
            # Determine readiness; limit to one question round
            ready = ("[READY]" in pm_response) or ("give me a moment" in pm_response.lower()) or force_build
            if not ready:
                if pm_rounds.get(project_id, 0) >= 1:
                    ready = True
                else:
                    pm_rounds[project_id] = pm_rounds.get(project_id, 0) + 1
            
            if ready:
                # Requirements complete - start agent workflow
                await websocket.send_json({
                    "type": "status",
                    "content": "📋 PM Agent creating task assignments..."
                })
            else:
                # Wait for user's next answer
                continue
                
                # Generate PM task document
                requirements = "\n".join([msg["content"] for msg in conversation_history[project_id] if msg["role"] == "user"])
                
                pm_doc_prompt = f"""Create a PM task assignment document for building this application:

User Requirements:
{requirements}

Generate a markdown document with:

# Project Management Document

## Project Overview
[Brief description]

## Requirements Summary
[List of key requirements]

## Task Assignments

### Backend Agent Tasks
- [ ] Task 1
- [ ] Task 2
...

### Frontend Agent Tasks
- [ ] Task 1
- [ ] Task 2
...

### QA Agent Tasks
- [ ] Task 1
- [ ] Task 2
...

Keep it clear and actionable."""

                pm_doc = await call_gemini(pm_doc_prompt)
                
                # Save PM document
                project_dir = PROJECTS_DIR / project_id
                project_dir.mkdir(exist_ok=True)
                
                pm_file = project_dir / "PM_TASKS.md"
                with open(pm_file, "w", encoding="utf-8") as f:
                    f.write(pm_doc)
                
                await websocket.send_json({
                    "type": "file_created",
                    "file": "PM_TASKS.md",
                    "content": pm_doc
                })
                
                # Backend Agent
                await websocket.send_json({
                    "type": "status",
                    "content": "⚙️ Backend Agent generating server code..."
                })
                
                backend_prompt = f"""You are a Backend Development AI Agent. Generate backend code based on:

{requirements}

Create a simple FastAPI backend with:
- API endpoints
- Data models
- CRUD operations

Return JSON:
{{
  "file": "backend.py",
  "content": "# Complete FastAPI code..."
}}"""

                backend_response = await call_gemini(backend_prompt)
                backend_json = extract_json(backend_response)
                
                if backend_json:
                    backend_file = project_dir / backend_json["file"]
                    with open(backend_file, "w", encoding="utf-8") as f:
                        f.write(backend_json["content"])
                    
                    await websocket.send_json({
                        "type": "file_created",
                        "file": backend_json["file"],
                        "content": backend_json["content"]
                    })
                
                # Frontend Agent
                await websocket.send_json({
                    "type": "status",
                    "content": "🎨 Frontend Agent designing UI..."
                })
                
                frontend_prompt = f"""You are a Frontend Development AI Agent. Create a beautiful, modern web UI for:

{requirements}

Generate HTML, CSS, JavaScript that:
- Has a professional design with gradients and animations
- Is fully responsive
- Has smooth interactions
- Uses modern CSS (flexbox, grid)

Return JSON with files array:
{{
  "files": [
    {{"name": "index.html", "content": "..."}},
    {{"name": "style.css", "content": "..."}},
    {{"name": "app.js", "content": "..."}}
  ]
}}"""

                frontend_response = await call_gemini(frontend_prompt)
                frontend_json = extract_json(frontend_response)
                
                if frontend_json and "files" in frontend_json:
                    for file_data in frontend_json["files"]:
                        file_path = project_dir / file_data["name"]
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(file_data["content"])
                        
                        await websocket.send_json({
                            "type": "file_created",
                            "file": file_data["name"],
                            "content": file_data["content"]
                        })
                
                # QA Agent
                await websocket.send_json({
                    "type": "status",
                    "content": "✅ QA Agent reviewing code..."
                })
                
                qa_prompt = f"""You are a QA Testing AI Agent. Review the generated code and create:

1. Test cases
2. Quality report
3. Recommendations

Return markdown format."""

                qa_response = await call_gemini(qa_prompt)
                
                qa_file = project_dir / "QA_REPORT.md"
                with open(qa_file, "w", encoding="utf-8") as f:
                    f.write(qa_response)
                
                await websocket.send_json({
                    "type": "file_created",
                    "file": "QA_REPORT.md",
                    "content": qa_response
                })
                
                # Complete
                await websocket.send_json({
                    "type": "complete",
                    "description": "All agents completed their tasks!",
                    "preview_url": f"/projects/{project_id}/index.html"
                })
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"Error: {str(e)}"
        })


def format_conversation(history):
    """Format conversation history"""
    return "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in history[-5:]])


def extract_json(text):
    """Extract JSON from text"""
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            return None
    return None


@app.get("/projects/{project_id}/{file_path:path}")
async def serve_project_file(project_id: str, file_path: str):
    """Serve generated project files"""
    file = PROJECTS_DIR / project_id / file_path
    if file.exists():
        return FileResponse(file)
    return {"error": "File not found"}


@app.get("/api/projects")
async def list_projects():
    """List saved projects with basic metadata and files present."""
    projects = []
    for p in PROJECTS_DIR.glob("project_*"):
        if p.is_dir():
            meta = {}
            meta_file = p / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            files = [f.name for f in p.iterdir() if f.is_file() and f.name not in {"conversation.json", "meta.json"}]
            projects.append({
                "id": p.name,
                "files": files,
                "last_updated": meta.get("last_updated")
            })
    # Sort by last_updated desc if available
    projects.sort(key=lambda x: x.get("last_updated") or "", reverse=True)
    return JSONResponse({"projects": projects})


@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str):
    """Return contents of known files for a project (html/css/js/md)."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return JSONResponse({"error": "Project not found"}, status_code=404)
    result = {}
    for name in ["index.html", "style.css", "app.js", "PM_TASKS.md", "QA_REPORT.md"]:
        f = project_dir / name
        if f.exists():
            try:
                result[name] = f.read_text(encoding="utf-8")
            except Exception:
                pass
    return JSONResponse({"files": result})


@app.get("/api/projects/{project_id}/chat")
async def get_project_chat(project_id: str):
    """Return stored chat history for a project."""
    hist = load_history(project_id)
    return JSONResponse({"history": hist})


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
