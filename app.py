"""
Multi-Agent AI Code Generator
PM Agent → Backend Agent → Frontend Agent → QA Agent
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
import os
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configure OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# Agents storage
AGENTS_DIR = Path("agents_data")
AGENTS_DIR.mkdir(exist_ok=True)
AGENTS_FILE = AGENTS_DIR / "agents.json"

# Store conversation history per project (in-memory cache)
conversation_history: dict[str, list] = {}
# Track PM questioning rounds to avoid long back-and-forth
pm_rounds: dict[str, int] = {}

def load_agents() -> list:
    """Load custom agents from disk."""
    try:
        if AGENTS_FILE.exists():
            return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []

def save_agents(agents: list):
    """Save custom agents to disk."""
    try:
        AGENTS_FILE.write_text(json.dumps(agents, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

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


async def call_openai(prompt: str) -> str:
    """Call OpenAI API with optimized settings"""
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-4" for better quality
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant specialized in software development and ERP systems."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096,
                top_p=0.95
            ),
            timeout=60.0
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        return "Request timeout. Please try again with a simpler request."
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return f"Error generating response: {str(e)}"


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket for multi-agent workflow"""
    await websocket.accept()
    print("✅ WebSocket connection accepted")
    # Defer project_id until first message; allows client to reconnect to existing project
    project_id: str | None = None
    
    try:
        while True:
            # Receive message
            print("📩 Waiting for message...")
            data = await websocket.receive_json()
            message = data.get("message", "")
            client_pid = (data.get("project_id") or "").strip() or None
            print(f"📨 Received message: {message[:50]}... (project: {client_pid})")
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
            
            pm_prompt = f"""You are a PM Agent for ERP systems (Inventory, CRM, HR, Finance, Sales, etc).

User request: "{message}"

Rules:
1. If NOT ERP-related: Reject politely, suggest ERP examples
2. If ERP but needs details: Ask 2-3 brief questions
3. If complete or user says "build/start/go": Say "Thank you! Give me a moment..." [READY]

Keep response under 150 words. One question round max."""

            if force_build:
                pm_response = "Thank you! I have all the requirements. Give me a moment to coordinate with my development team... [READY]"
            else:
                print("🤖 Calling OpenAI API for PM response...")
                pm_response = await call_openai(pm_prompt)
                print(f"✅ PM response received: {pm_response[:100]}...")
            
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
            
            if not ready:
                # Wait for user's next answer
                continue
            
            # Requirements complete - start agent workflow
            await websocket.send_json({
                "type": "status",
                "content": "📋 PM Agent creating task assignments..."
            })
            
            # Generate PM task document
            requirements = "\n".join([msg["content"] for msg in conversation_history[project_id] if msg["role"] == "user"])
            
            pm_doc_prompt = f"""Create PM doc for: {requirements[:200]}

Format:
# Project: [Name]
## Requirements: [3-5 key items]
## Tasks:
- Backend: [3 tasks]
- Frontend: [3 tasks]  
- QA: [2 tasks]

Keep under 200 words."""

            pm_doc = await call_openai(pm_doc_prompt)
            
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
            
            backend_prompt = f"""Create FastAPI backend for: {requirements[:300]}

Return ONLY valid JSON:
{{"file": "backend.py", "content": "# FastAPI code with endpoints, models, CRUD"}}

Keep code under 200 lines."""

            backend_response = await call_openai(backend_prompt)
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
            
            frontend_prompt = f"""Create modern responsive UI for: {requirements[:300]}

Return ONLY valid JSON:
{{"files": [{{"name": "index.html", "content": "..."}}, {{"name": "style.css", "content": "..."}}, {{"name": "app.js", "content": "..."}}]}}

Use gradients, modern CSS. Keep each file under 150 lines."""

            frontend_response = await call_openai(frontend_prompt)
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
            
            qa_prompt = f"""QA Report for {requirements[:150]}

Provide:
- 3 test cases
- Quality score (1-10)
- 2 recommendations

Keep under 150 words."""

            qa_response = await call_openai(qa_prompt)
            
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
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Error: {str(e)}"
            })
        except:
            pass


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


# ============ AGENT MANAGEMENT API ============

class AgentCreate(BaseModel):
    name: str
    role: str
    model: str
    prompt: str


@app.get("/api/agents")
async def list_agents():
    """List all custom agents."""
    agents = load_agents()
    return JSONResponse({"agents": agents})


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    agents = load_agents()
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return JSONResponse(agent)


@app.post("/api/agents")
async def create_agent(agent: AgentCreate):
    """Create a new custom agent."""
    agents = load_agents()
    
    # Generate unique ID
    agent_id = f"agent_{int(datetime.utcnow().timestamp() * 1000)}"
    
    new_agent = {
        "id": agent_id,
        "name": agent.name,
        "role": agent.role,
        "model": agent.model,
        "prompt": agent.prompt,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    agents.append(new_agent)
    save_agents(agents)
    
    return JSONResponse(new_agent, status_code=201)


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete a custom agent."""
    agents = load_agents()
    agents = [a for a in agents if a["id"] != agent_id]
    save_agents(agents)
    return JSONResponse({"message": "Agent deleted successfully"})


# ============ PAGE ROUTES ============

@app.get("/create-agent")
async def create_agent_page():
    """Serve create agent page."""
    with open("static/create-agent.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/automation")
async def automation_page():
    """Serve automation page."""
    with open("static/automation.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
