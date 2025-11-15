from typing import List, Dict
from pathlib import Path

from app.ingestion.parsers import DocumentParser, DocumentChunker
from app.services.rag_service import RAGService


class DocumentIngestion:
    """Orchestrate document parsing, chunking, and embedding."""
    
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.parser = DocumentParser()
        self.chunker = DocumentChunker()
    
    async def ingest_document(
        self, 
        file_path: str, 
        project_id: str,
        chunk_size: int = 1000
    ) -> Dict[str, any]:
        """Parse, chunk, and embed a document into the RAG system."""
        
        # Parse document
        parsed_doc = self.parser.parse_document(file_path)
        
        if "error" in parsed_doc:
            return {
                "success": False,
                "filename": parsed_doc["filename"],
                "error": parsed_doc["error"]
            }
        
        # Chunk document
        chunks = self.chunker.chunk_document(parsed_doc, chunk_size)
        
        if not chunks:
            return {
                "success": False,
                "filename": parsed_doc["filename"],
                "error": "No content could be extracted"
            }
        
        # Prepare for embedding
        documents = [chunk["text"] for chunk in chunks]
        metadatas = []
        ids = []
        
        filename = parsed_doc["filename"]
        
        for i, chunk in enumerate(chunks):
            metadata = chunk["metadata"].copy()
            metadata["project_id"] = project_id
            metadatas.append(metadata)
            
            # Generate unique ID
            ids.append(f"{project_id}_{filename}_{i}")
        
        # Add to vector database
        self.rag_service.add_documents(documents, metadatas, ids)
        
        return {
            "success": True,
            "filename": filename,
            "type": parsed_doc["type"],
            "chunks_created": len(chunks),
            "project_id": project_id
        }
    
    async def ingest_multiple_documents(
        self, 
        file_paths: List[str], 
        project_id: str
    ) -> List[Dict]:
        """Ingest multiple documents."""
        results = []
        
        for file_path in file_paths:
            result = await self.ingest_document(file_path, project_id)
            results.append(result)
        
        return results
    
    def get_project_context(self, project_id: str, query: str) -> str:
        """Get relevant context for a query within a project."""
        return self.rag_service.get_context_for_query(query, project_id)
