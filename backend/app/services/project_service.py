"""
RAG Project Manager Service (Backend)
Manages projects and their document collections.
"""

import hashlib
import json
import os
from datetime import datetime

import structlog
from app.services.rag_service import rag_service

logger = structlog.get_logger()

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

class ProjectService:
    def __init__(self, projects_file: str = None):
        """Initialize Project Manager"""
        self.projects_file = projects_file or os.path.join(DATA_DIR, "projects.json")
        self.projects = self._load_projects()
    
    def _load_projects(self) -> list[dict]:
        """Load projects from file"""
        if not os.path.exists(self.projects_file):
            return []
        
        try:
            with open(self.projects_file, encoding='utf-8') as f:
                data = json.load(f)
                return data.get('projects', [])
        except Exception as e:
            logger.error("Error loading projects", error=str(e))
            return []
    
    def _save_projects(self):
        """Save projects to file"""
        try:
            os.makedirs(os.path.dirname(self.projects_file), exist_ok=True)
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump({'projects': self.projects}, f, ensure_ascii=False, indent=2)
            logger.info("Projects saved", file=self.projects_file)
        except Exception as e:
            logger.error("Error saving projects", error=str(e))
    
    def list_projects(self) -> list[dict]:
        """List all projects"""
        return self.projects
    
    def create_project(self, name: str, description: str = "") -> str | None:
        """Create a new project"""
        if any(p['name'] == name for p in self.projects):
            logger.warning(f"Project '{name}' exists")
            return None
        
        project_id = f"proj_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        project = {
            "id": project_id,
            "name": name,
            "description": description,
            "collections": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.projects.append(project)
        self._save_projects()
        logger.info(f"Created project: {name}", id=project_id)
        return project_id
    
    def get_project(self, project_id: str) -> dict | None:
        """Get project info"""
        for proj in self.projects:
            if proj['id'] == project_id:
                return proj
        return None
    
    def update_project(self, project_id: str, name: str = None, description: str = None) -> bool:
        """Update project info"""
        for proj in self.projects:
            if proj['id'] == project_id:
                if name: proj['name'] = name
                if description is not None: proj['description'] = description
                proj['updated_at'] = datetime.now().isoformat()
                self._save_projects()
                return True
        return False
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project"""
        for i, proj in enumerate(self.projects):
            if proj['id'] == project_id:
                del self.projects[i]
                self._save_projects()
                logger.info(f"Deleted project: {project_id}")
                return True
        return False
    
    def add_to_project(self, project_id: str, collection_name: str) -> bool:
        """Add document collection to project"""
        for proj in self.projects:
            if proj['id'] == project_id:
                if collection_name not in proj['collections']:
                    proj['collections'].append(collection_name)
                    proj['updated_at'] = datetime.now().isoformat()
                    self._save_projects()
                    logger.info(f"Added {collection_name} to {project_id}")
                    return True
                return False
        return False
    
    def remove_from_project(self, project_id: str, collection_name: str) -> bool:
        """Remove document collection from project"""
        for proj in self.projects:
            if proj['id'] == project_id:
                if collection_name in proj['collections']:
                    proj['collections'].remove(collection_name)
                    proj['updated_at'] = datetime.now().isoformat()
                    self._save_projects()
                    logger.info(f"Removed {collection_name} from {project_id}")
                    return True
        return False
    
    def get_project_stats(self, project_id: str) -> dict:
        """Get project statistics"""
        proj = self.get_project(project_id)
        if not proj: return {}
        
        collections = proj.get('collections', [])
        total_chunks = 0
        
        # We need to query RAG service for doc stats
        # Assuming rag_service is available in backend
        indexed_docs = rag_service.list_indexed_documents()
        
        for col_name in collections:
            doc = next((d for d in indexed_docs if d['collection_name'] == col_name), None)
            if doc:
                total_chunks += doc.get('count', 0)
        
        return {
            'total_documents': len(collections),
            'total_chunks': total_chunks
        }

project_service = ProjectService()
