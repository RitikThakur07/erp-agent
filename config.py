from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # LLM Configuration
    llm_provider: str = "gemini"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    local_model_path: Optional[str] = None
    
    # Model Settings
    default_model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # Embeddings
    embeddings_provider: str = "openai"
    embeddings_model: str = "text-embedding-3-small"
    
    # Vector Database
    vector_db_path: str = "./data/chroma"
    vector_collection: str = "erp_documents"
    
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    workspace_root: str = "./workspace"
    upload_dir: str = "./uploads"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/erp_builder.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        Path(self.workspace_root).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)
        Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
