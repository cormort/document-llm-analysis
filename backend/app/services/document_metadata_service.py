import json
import os
from datetime import datetime

import structlog

logger = structlog.get_logger()

# Define data directory for backend
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

class DocumentMetadataService:
    """Manage custom document metadata (display name, description, tags)"""

    def __init__(self, persist_path: str = None):
        """Initialize metadata service"""
        self.persist_path = persist_path or os.path.join(DATA_DIR, "document_metadata.json")
        self._metadata: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load metadata from file"""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, encoding="utf-8") as f:
                    self._metadata = json.load(f)
                logger.info("Loaded document metadata", count=len(self._metadata))
            except Exception as e:
                logger.error("Failed to load metadata", error=str(e))
                self._metadata = {}
        else:
            self._metadata = {}

    def _save(self) -> None:
        """Save metadata to file"""
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
            logger.info("Saved document metadata", count=len(self._metadata))
        except Exception as e:
            logger.error("Failed to save metadata", error=str(e))

    def get_metadata(self, collection_name: str) -> dict:
        """Get metadata for a collection"""
        return self._metadata.get(collection_name, {})

    def get_display_name(self, collection_name: str, fallback: str = "Unknown") -> str:
        """Get display name"""
        meta = self.get_metadata(collection_name)
        return meta.get("display_name") or meta.get("original_file_name") or fallback

    def update_metadata(
        self,
        collection_name: str,
        display_name: str = None,
        description: str = None,
        tags: list[str] = None,
        original_file_name: str = None,
    ) -> bool:
        """Update metadata"""
        try:
            now = datetime.now().isoformat()
            if collection_name not in self._metadata:
                self._metadata[collection_name] = {"created_at": now}

            entry = self._metadata[collection_name]

            if display_name is not None:
                entry["display_name"] = display_name.strip()
            if description is not None:
                entry["description"] = description.strip()
            if tags is not None:
                entry["tags"] = [t.strip() for t in tags if t.strip()]
            if original_file_name is not None:
                entry["original_file_name"] = original_file_name

            entry["updated_at"] = now
            self._save()
            return True
        except Exception as e:
            logger.error("Failed to update metadata", collection=collection_name, error=str(e))
            return False

    def delete_metadata(self, collection_name: str) -> bool:
        """Delete metadata"""
        if collection_name in self._metadata:
            del self._metadata[collection_name]
            self._save()
            return True
        return False

    def list_all(self) -> dict[str, dict]:
        """List all metadata"""
        return self._metadata.copy()

    def search_by_tag(self, tag: str) -> list[str]:
        """Search by tag"""
        results = []
        tag_lower = tag.lower()
        for collection_name, meta in self._metadata.items():
            tags = meta.get("tags", [])
            if any(tag_lower in t.lower() for t in tags):
                results.append(collection_name)
        return results

document_metadata_service = DocumentMetadataService()
