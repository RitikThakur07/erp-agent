from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os


class RAGService:
    """Retrieval-Augmented Generation service for document querying."""
    
    def __init__(
        self, 
        db_path: str = "./data/chroma",
        collection_name: str = "erp_documents",
        embeddings_provider: str = "local"
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embeddings_provider = embeddings_provider
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embeddings
        if embeddings_provider == "local":
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        elif embeddings_provider == "openai":
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.embeddings_model = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if self.embeddings_provider == "local":
            return self.embedder.encode(texts).tolist()
        
        elif self.embeddings_provider == "openai":
            response = self.openai_client.embeddings.create(
                model=self.embeddings_model,
                input=texts
            )
            return [item.embedding for item in response.data]
    
    def add_documents(
        self, 
        documents: List[str], 
        metadatas: List[Dict], 
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to the vector database."""
        if not ids:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        embeddings = self.get_embeddings(documents)
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(
        self, 
        query_text: str, 
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, List]:
        """Query the vector database for relevant documents."""
        query_embedding = self.get_embeddings([query_text])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }
    
    def delete_project_documents(self, project_id: str) -> None:
        """Delete all documents for a specific project."""
        results = self.collection.get(
            where={"project_id": project_id}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def get_context_for_query(
        self, 
        query: str, 
        project_id: Optional[str] = None,
        max_results: int = 3
    ) -> str:
        """Get relevant context for a query as formatted text."""
        filter_metadata = {"project_id": project_id} if project_id else None
        
        results = self.query(query, n_results=max_results, filter_metadata=filter_metadata)
        
        if not results["documents"]:
            return ""
        
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
            source = metadata.get("source", "Unknown")
            context_parts.append(f"[Source: {source}]\n{doc}\n")
        
        return "\n---\n".join(context_parts)
