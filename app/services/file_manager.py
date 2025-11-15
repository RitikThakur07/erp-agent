import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class FileManager:
    """Manages file operations for generated ERP projects."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def create_project_structure(self, project_id: str) -> Dict[str, str]:
        """Create the folder structure for a new ERP project."""
        project_path = self.workspace_root / f"project_{project_id}"
        
        # Create main directories
        backend_path = project_path / "backend"
        frontend_path = project_path / "frontend"
        
        # Backend structure
        (backend_path / "app").mkdir(parents=True, exist_ok=True)
        (backend_path / "app" / "models").mkdir(exist_ok=True)
        (backend_path / "app" / "routers").mkdir(exist_ok=True)
        (backend_path / "app" / "services").mkdir(exist_ok=True)
        (backend_path / "app" / "schemas").mkdir(exist_ok=True)
        (backend_path / "tests").mkdir(exist_ok=True)
        
        # Frontend structure
        (frontend_path / "templates").mkdir(parents=True, exist_ok=True)
        (frontend_path / "static" / "css").mkdir(parents=True, exist_ok=True)
        (frontend_path / "static" / "js").mkdir(exist_ok=True)
        
        return {
            "project_path": str(project_path),
            "backend_path": str(backend_path),
            "frontend_path": str(frontend_path)
        }
    
    def write_file(self, project_id: str, relative_path: str, content: str) -> str:
        """Write content to a file in the project workspace."""
        project_path = self.workspace_root / f"project_{project_id}"
        file_path = project_path / relative_path
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        
        return str(file_path)
    
    def read_file(self, project_id: str, relative_path: str) -> Optional[str]:
        """Read content from a file in the project workspace."""
        project_path = self.workspace_root / f"project_{project_id}"
        file_path = project_path / relative_path
        
        if not file_path.exists():
            return None
        
        return file_path.read_text(encoding="utf-8")
    
    def list_files(self, project_id: str, directory: str = "") -> List[Dict[str, any]]:
        """List all files in a project directory recursively."""
        project_path = self.workspace_root / f"project_{project_id}"
        target_path = project_path / directory if directory else project_path
        
        if not target_path.exists():
            return []
        
        files = []
        for item in target_path.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(project_path)
                files.append({
                    "path": str(relative_path).replace("\\", "/"),
                    "name": item.name,
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
        
        return files
    
    def get_file_tree(self, project_id: str) -> Dict:
        """Generate a hierarchical file tree structure."""
        project_path = self.workspace_root / f"project_{project_id}"
        
        if not project_path.exists():
            return {}
        
        def build_tree(path: Path) -> Dict:
            tree = {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "path": str(path.relative_to(project_path)).replace("\\", "/")
            }
            
            if path.is_dir():
                children = []
                for child in sorted(path.iterdir()):
                    if child.name.startswith("."):
                        continue
                    children.append(build_tree(child))
                tree["children"] = children
            
            return tree
        
        return build_tree(project_path)
    
    def delete_project(self, project_id: str) -> bool:
        """Delete an entire project directory."""
        project_path = self.workspace_root / f"project_{project_id}"
        
        if project_path.exists():
            shutil.rmtree(project_path)
            return True
        
        return False
    
    def save_metadata(self, project_id: str, metadata: Dict) -> None:
        """Save project metadata."""
        project_path = self.workspace_root / f"project_{project_id}"
        metadata_file = project_path / "metadata.json"
        
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    def load_metadata(self, project_id: str) -> Optional[Dict]:
        """Load project metadata."""
        project_path = self.workspace_root / f"project_{project_id}"
        metadata_file = project_path / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        return json.loads(metadata_file.read_text(encoding="utf-8"))
