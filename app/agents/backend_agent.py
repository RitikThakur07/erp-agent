from typing import Dict, List
from app.services.llm_adapter import LLMAdapter
from app.services.file_manager import FileManager


class BackendAgent:
    """Backend Agent - Generates FastAPI backend code."""
    
    SYSTEM_PROMPT = """You are an expert FastAPI backend developer specialized in building ERP systems.

Your responsibilities:
1. Generate production-ready FastAPI code based on PRD
2. Create proper SQLAlchemy models with relationships
3. Implement CRUD operations and business logic
4. Generate API routers with proper validation
5. Follow best practices and clean code principles

Architecture:
- app/models/ - SQLAlchemy ORM models
- app/schemas/ - Pydantic schemas for validation
- app/routers/ - API endpoints
- app/services/ - Business logic
- app/database.py - Database configuration
- app/main.py - FastAPI application

Generate modular, well-documented, production-ready code."""
    
    def __init__(self, llm_adapter: LLMAdapter, file_manager: FileManager):
        self.llm = llm_adapter
        self.file_manager = file_manager
    
    async def generate_backend(self, project_id: str, prd: Dict) -> Dict[str, any]:
        """Generate complete FastAPI backend from PRD."""
        
        try:
            # Generate each component
            results = {
                "models": await self._generate_models(project_id, prd),
                "schemas": await self._generate_schemas(project_id, prd),
                "database": await self._generate_database_config(project_id, prd),
                "routers": await self._generate_routers(project_id, prd),
                "services": await self._generate_services(project_id, prd),
                "main": await self._generate_main_app(project_id, prd)
            }
            
            return {
                "success": True,
                "project_id": project_id,
                "files_generated": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_models(self, project_id: str, prd: Dict) -> List[str]:
        """Generate SQLAlchemy models."""
        files_created = []
        
        entities = prd.get("entities", [])
        
        for entity in entities:
            prompt = f"""Generate a complete SQLAlchemy model for this entity:

Entity: {entity['name']}
Description: {entity.get('description', '')}
Fields: {entity.get('fields', [])}

Include:
- Proper imports
- Table relationships if applicable
- Indexes for common queries
- String representations
- Timestamps (created_at, updated_at)

Generate ONLY the Python code, no explanations."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            
            # Clean code
            code = self._clean_code(code)
            
            # Write to file
            filename = f"backend/app/models/{entity['name'].lower()}.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        # Generate __init__.py for models
        init_code = self._generate_models_init(entities)
        init_file = "backend/app/models/__init__.py"
        self.file_manager.write_file(project_id, init_file, init_code)
        files_created.append(init_file)
        
        return files_created
    
    async def _generate_schemas(self, project_id: str, prd: Dict) -> List[str]:
        """Generate Pydantic schemas."""
        files_created = []
        
        entities = prd.get("entities", [])
        
        for entity in entities:
            prompt = f"""Generate Pydantic schemas for this entity:

Entity: {entity['name']}
Fields: {entity.get('fields', [])}

Create these schemas:
1. {entity['name']}Base - Base schema with common fields
2. {entity['name']}Create - For POST requests
3. {entity['name']}Update - For PUT/PATCH requests
4. {entity['name']}Response - For responses (includes ID, timestamps)

Generate ONLY the Python code with proper imports."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/app/schemas/{entity['name'].lower()}.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        return files_created
    
    async def _generate_routers(self, project_id: str, prd: Dict) -> List[str]:
        """Generate API routers."""
        files_created = []
        
        modules = prd.get("modules", [])
        
        for module in modules:
            prompt = f"""Generate a FastAPI router for this module:

Module: {module['name']}
Description: {module.get('description', '')}
Features: {module.get('features', [])}

Create CRUD endpoints:
- GET /{{module}} - List all
- GET /{{module}}/{{id}} - Get one
- POST /{{module}} - Create
- PUT /{{module}}/{{id}} - Update
- DELETE /{{module}}/{{id}} - Delete

Include proper:
- Dependency injection
- Response models
- Error handling
- Pagination for list endpoints

Generate ONLY the Python code."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/app/routers/{module['name'].lower().replace(' ', '_')}.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        return files_created
    
    async def _generate_services(self, project_id: str, prd: Dict) -> List[str]:
        """Generate business logic services."""
        files_created = []
        
        entities = prd.get("entities", [])
        
        for entity in entities:
            prompt = f"""Generate a service class for this entity:

Entity: {entity['name']}

Include CRUD operations:
- create
- get_by_id
- get_all (with pagination)
- update
- delete

Use async/await with SQLAlchemy async session.
Generate ONLY the Python code."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/app/services/{entity['name'].lower()}_service.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        return files_created
    
    async def _generate_database_config(self, project_id: str, prd: Dict) -> List[str]:
        """Generate database configuration."""
        code = """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./erp.db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
"""
        
        filename = "backend/app/database.py"
        self.file_manager.write_file(project_id, filename, code)
        
        return [filename]
    
    async def _generate_main_app(self, project_id: str, prd: Dict) -> List[str]:
        """Generate main FastAPI application."""
        modules = prd.get("modules", [])
        router_imports = "\n".join([
            f"from app.routers import {m['name'].lower().replace(' ', '_')}"
            for m in modules
        ])
        
        router_includes = "\n    ".join([
            f"app.include_router({m['name'].lower().replace(' ', '_')}.router)"
            for m in modules
        ])
        
        code = f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
{router_imports}

app = FastAPI(title="{prd.get('project_name', 'ERP System')}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{router_includes}

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
def root():
    return {{"message": "ERP API is running"}}
"""
        
        filename = "backend/app/main.py"
        self.file_manager.write_file(project_id, filename, code)
        
        # Also create requirements.txt
        requirements = """fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
aiosqlite==0.19.0
pydantic==2.5.3
python-dotenv==1.0.1
"""
        self.file_manager.write_file(project_id, "backend/requirements.txt", requirements)
        
        return [filename, "backend/requirements.txt"]
    
    def _clean_code(self, code: str) -> str:
        """Clean generated code."""
        # Remove markdown formatting
        cleaned = code.strip()
        if cleaned.startswith("```python"):
            cleaned = cleaned[9:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return cleaned.strip()
    
    def _generate_models_init(self, entities: List[Dict]) -> str:
        """Generate __init__.py for models package."""
        imports = "\n".join([
            f"from app.models.{e['name'].lower()} import {e['name']}"
            for e in entities
        ])
        
        all_list = ", ".join([f'"{e["name"]}"' for e in entities])
        
        return f"{imports}\n\n__all__ = [{all_list}]\n"
