import uuid
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from app.services.file_manager import FileManager


class Workspace:
    """Manages ERP project workspaces and lifecycle."""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.active_projects: Dict[str, Dict] = {}
    
    def create_project(self, name: str, description: str = "") -> Dict[str, any]:
        """Create a new ERP project workspace."""
        project_id = str(uuid.uuid4())[:8]
        
        # Create folder structure
        paths = self.file_manager.create_project_structure(project_id)
        
        # Initialize metadata
        metadata = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "status": "initializing",
            "prd": None,
            "backend_generated": False,
            "frontend_generated": False,
            "qa_completed": False
        }
        
        self.file_manager.save_metadata(project_id, metadata)
        self.active_projects[project_id] = metadata
        
        return {
            "project_id": project_id,
            "metadata": metadata,
            "paths": paths
        }
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get project metadata."""
        if project_id in self.active_projects:
            return self.active_projects[project_id]
        
        # Load from disk
        metadata = self.file_manager.load_metadata(project_id)
        if metadata:
            self.active_projects[project_id] = metadata
        
        return metadata
    
    def update_project_status(self, project_id: str, status: str, **kwargs) -> None:
        """Update project status and additional fields."""
        metadata = self.get_project(project_id)
        if not metadata:
            raise ValueError(f"Project {project_id} not found")
        
        metadata["status"] = status
        metadata["updated_at"] = datetime.utcnow().isoformat()
        
        for key, value in kwargs.items():
            metadata[key] = value
        
        self.file_manager.save_metadata(project_id, metadata)
        self.active_projects[project_id] = metadata
    
    def save_prd(self, project_id: str, prd: Dict) -> None:
        """Save the Product Requirements Document."""
        self.update_project_status(project_id, "prd_approved", prd=prd)
        
        # Also save as a separate file
        prd_content = self._format_prd(prd)
        self.file_manager.write_file(project_id, "PRD.md", prd_content)
    
    def _format_prd(self, prd: Dict) -> str:
        """Format PRD as markdown."""
        sections = [
            f"# Product Requirements Document\n",
            f"## Project Overview\n{prd.get('overview', '')}\n",
            f"## Modules\n"
        ]
        
        for module in prd.get("modules", []):
            sections.append(f"### {module.get('name', 'Module')}\n")
            sections.append(f"{module.get('description', '')}\n")
        
        sections.append(f"\n## Database Entities\n")
        for entity in prd.get("entities", []):
            sections.append(f"### {entity.get('name', 'Entity')}\n")
            sections.append(f"Fields: {', '.join(entity.get('fields', []))}\n")
        
        sections.append(f"\n## User Roles\n")
        for role in prd.get("roles", []):
            sections.append(f"- {role}\n")
        
        return "\n".join(sections)
    
    def mark_backend_complete(self, project_id: str) -> None:
        """Mark backend generation as complete."""
        self.update_project_status(project_id, "backend_complete", backend_generated=True)
    
    def mark_frontend_complete(self, project_id: str) -> None:
        """Mark frontend generation as complete."""
        self.update_project_status(project_id, "frontend_complete", frontend_generated=True)
    
    def mark_qa_complete(self, project_id: str, qa_results: Dict) -> None:
        """Mark QA as complete with results."""
        self.update_project_status(
            project_id, 
            "qa_complete", 
            qa_completed=True,
            qa_results=qa_results
        )
    
    def list_all_projects(self) -> list:
        """List all projects in workspace."""
        workspace_path = Path(self.file_manager.workspace_root)
        projects = []
        
        for project_dir in workspace_path.glob("project_*"):
            if project_dir.is_dir():
                project_id = project_dir.name.replace("project_", "")
                metadata = self.get_project(project_id)
                if metadata:
                    projects.append(metadata)
        
        return projects
