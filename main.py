from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from pathlib import Path

from config import settings
from app.services import FileManager, Workspace, LLMAdapter, RAGService
from app.ingestion import DocumentIngestion
from app.agents import PMAgent, BackendAgent, FrontendAgent, QAAgent


# Initialize FastAPI app
app = FastAPI(
    title="ERP Builder",
    description="Local-first ERP Builder powered by multi-agents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="app/templates")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize services
file_manager = FileManager(settings.workspace_root)
workspace = Workspace(file_manager)
llm_adapter = LLMAdapter(
    provider=settings.llm_provider,
    model=settings.default_model,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens
)
rag_service = RAGService(
    db_path=settings.vector_db_path,
    collection_name=settings.vector_collection,
    embeddings_provider=settings.embeddings_provider
)
document_ingestion = DocumentIngestion(rag_service)

# Initialize agents
pm_agent = PMAgent(llm_adapter, rag_service)
backend_agent = BackendAgent(llm_adapter, file_manager)
frontend_agent = FrontendAgent(llm_adapter, file_manager)
qa_agent = QAAgent(llm_adapter, file_manager)


# Pydantic models
class ChatRequest(BaseModel):
    project_id: str
    message: str

class ChatResponse(BaseModel):
    message: str
    is_prd: bool
    project_id: str

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class AgentRequest(BaseModel):
    project_id: str
    prd: Optional[dict] = None


# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main application page."""
    projects = workspace.list_all_projects()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "projects": projects}
    )


@app.post("/projects/create")
async def create_project(project: ProjectCreate):
    """Create a new ERP project."""
    result = workspace.create_project(project.name, project.description)
    return JSONResponse(content=result)


@app.get("/projects")
async def list_projects():
    """List all projects."""
    projects = workspace.list_all_projects()
    return JSONResponse(content={"projects": projects})


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = workspace.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return JSONResponse(content=project)


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with PM Agent."""
    try:
        response = await pm_agent.chat(request.project_id, request.message)
        return JSONResponse(content=response)
    except Exception as e:
        raise e
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/generate-prd")
async def generate_prd(request: AgentRequest):
    """Generate PRD from conversation."""
    try:
        result = await pm_agent.generate_prd(request.project_id)
        
        if result.get("success"):
            # Save PRD to workspace
            workspace.save_prd(request.project_id, result["prd"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/backend")
async def trigger_backend_agent(request: AgentRequest):
    """Trigger backend code generation."""
    try:
        # Get PRD from workspace if not provided
        if not request.prd:
            project = workspace.get_project(request.project_id)
            if not project or not project.get("prd"):
                raise HTTPException(status_code=400, detail="PRD not found")
            request.prd = project["prd"]
        
        result = await backend_agent.generate_backend(request.project_id, request.prd)
        
        if result.get("success"):
            workspace.mark_backend_complete(request.project_id)
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/frontend")
async def trigger_frontend_agent(request: AgentRequest):
    """Trigger frontend code generation."""
    try:
        # Get PRD from workspace if not provided
        if not request.prd:
            project = workspace.get_project(request.project_id)
            if not project or not project.get("prd"):
                raise HTTPException(status_code=400, detail="PRD not found")
            request.prd = project["prd"]
        
        result = await frontend_agent.generate_frontend(request.project_id, request.prd)
        
        if result.get("success"):
            workspace.mark_frontend_complete(request.project_id)
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/qa")
async def trigger_qa_agent(request: AgentRequest):
    """Trigger QA agent."""
    try:
        # Get PRD from workspace if not provided
        if not request.prd:
            project = workspace.get_project(request.project_id)
            if not project or not project.get("prd"):
                raise HTTPException(status_code=400, detail="PRD not found")
            request.prd = project["prd"]
        
        result = await qa_agent.run_qa(request.project_id, request.prd)
        
        if result.get("success"):
            workspace.mark_qa_complete(request.project_id, result["qa_results"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(project_id: str, file: UploadFile = File(...)):
    """Upload and ingest a document for RAG."""
    try:
        # Save uploaded file
        upload_path = Path(settings.upload_dir) / project_id
        upload_path.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_path / file.filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Ingest document
        result = await document_ingestion.ingest_document(
            str(file_path),
            project_id
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/files")
async def list_project_files(project_id: str, directory: str = ""):
    """List files in project workspace."""
    try:
        files = file_manager.list_files(project_id, directory)
        return JSONResponse(content={"files": files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/file-tree")
async def get_file_tree(project_id: str):
    """Get hierarchical file tree."""
    try:
        tree = file_manager.get_file_tree(project_id)
        return JSONResponse(content=tree)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/file")
async def read_file(project_id: str, path: str):
    """Read file content."""
    try:
        content = file_manager.read_file(project_id, path)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        return JSONResponse(content={"path": path, "content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/file")
async def write_file(project_id: str, path: str, content: str):
    """Write file content."""
    try:
        file_path = file_manager.write_file(project_id, path, content)
        return JSONResponse(content={"path": file_path, "success": True})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/preview/{project_id}/{path:path}")
async def preview_generated_app(project_id: str, path: str):
    """Serve generated frontend for preview."""
    try:
        # Serve frontend files
        frontend_path = Path(settings.workspace_root) / f"project_{project_id}" / "frontend"
        
        if not path or path == "/":
            path = "templates/dashboard.html"
        
        file_path = frontend_path / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    try:
        success = file_manager.delete_project(project_id)
        
        # Also delete from RAG
        rag_service.delete_project_documents(project_id)
        
        return JSONResponse(content={"success": success})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy", "version": "1.0.0"})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
