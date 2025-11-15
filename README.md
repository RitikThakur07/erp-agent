# ERP Builder - Local-First AI-Powered ERP Generator

A production-ready, local-first ERP Builder powered by multi-agent AI architecture. Build complete ERP systems through natural conversation with AI agents.

## 🌟 Features

- **Multi-Agent Architecture**: Specialized AI agents for PM, Backend, Frontend, and QA
- **Conversational Requirements Gathering**: Chat-based interface for collecting ERP requirements
- **Automatic Code Generation**: Generate FastAPI backend and HTML/Jinja2 frontend
- **RAG-Powered Context**: Upload documents (PDF, DOCX, XLSX) for intelligent context
- **Live Code Editor**: Monaco editor with syntax highlighting
- **File Management**: Full file tree navigation and editing
- **Quality Assurance**: Automated test generation and code validation
- **Local-First**: All data and generated code stored locally

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (HTML/HTMX)               │
│  ┌──────────────┬───────────────────┬──────────────────┐   │
│  │  Chat Panel  │   Code Editor     │  Preview Panel   │   │
│  │   (PM Agent) │  (Monaco Editor)  │  (Actions/View)  │   │
│  └──────────────┴───────────────────┴──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  FastAPI Server  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │   PM    │        │ Backend │        │Frontend │
    │  Agent  │        │  Agent  │        │  Agent  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                        ┌────▼────┐
                        │   QA    │
                        │  Agent  │
                        └────┬────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │   LLM   │        │   RAG   │        │  File   │
    │ Adapter │        │ Service │        │ Manager │
    └─────────┘        └─────────┘        └─────────┘
```

## 📋 Prerequisites

- Python 3.9+
- OpenAI API Key (or Anthropic/Local LLM)
- 4GB+ RAM
- Modern web browser

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd c:\Users\ritik\OneDrive\Desktop\poc

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your API keys
notepad .env
```

Required configuration:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
EMBEDDINGS_PROVIDER=openai
```

### 3. Run Application

```bash
python main.py
```

Open browser: `http://localhost:8000`

## 📖 User Guide

### Creating Your First ERP System

1. **Create New Project**
   - Click "+ New Project"
   - Enter project name (e.g., "Warehouse Management System")
   - Add description

2. **Chat with PM Agent**
   ```
   You: I need an inventory management system for a warehouse
   PM: Great! Let me ask you some questions...
   - What types of products do you manage?
   - Do you need multi-location support?
   - What user roles do you need?
   ```

3. **Upload Context Documents** (Optional)
   - Click 📎 Upload Document
   - Support for: PDF, DOCX, XLSX, TXT, MD
   - Documents are embedded in RAG for intelligent context

4. **Generate PRD**
   - After requirements discussion, click "Generate PRD"
   - PM Agent creates structured Product Requirements Document

5. **Generate Backend**
   - Click "🔧 Generate Backend"
   - Backend Agent creates:
     - SQLAlchemy models
     - Pydantic schemas
     - FastAPI routers
     - Business logic services
     - Database configuration

6. **Generate Frontend**
   - Click "🎨 Generate Frontend"
   - Frontend Agent creates:
     - Jinja2 templates
     - HTML forms and tables
     - TailwindCSS styling
     - HTMX interactions

7. **Run QA**
   - Click "✓ Run QA Tests"
   - QA Agent generates:
     - Pytest unit tests
     - Integration tests
     - Test fixtures
     - Code validation report

8. **Edit & Preview**
   - Browse file tree in code panel
   - Click files to edit in Monaco editor
   - View live preview in preview panel

## 🤖 Agent Specifications

### PM Agent (Project Manager)
**Responsibilities:**
- Collect ERP requirements through conversation
- Ask clarifying questions about modules, roles, entities
- Generate comprehensive PRD in structured JSON format
- Utilize RAG for context from uploaded documents

**Example Conversation:**
```
PM: What kind of ERP system would you like to build?
User: Inventory management for a retail store
PM: Excellent! A few questions:
1. How many product categories do you have?
2. Do you need barcode/SKU tracking?
3. Will you track stock across multiple locations?
4. What reports do you need?
```

### Backend Agent
**Responsibilities:**
- Convert PRD → FastAPI application
- Generate SQLAlchemy models with relationships
- Create Pydantic schemas for validation
- Build CRUD API endpoints
- Implement business logic services

**Generated Structure:**
```
backend/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # API endpoints
│   ├── services/        # Business logic
│   ├── database.py      # DB configuration
│   └── main.py          # FastAPI app
├── tests/               # Pytest tests
└── requirements.txt
```

### Frontend Agent
**Responsibilities:**
- Generate HTML/Jinja2 templates
- Create responsive UI with TailwindCSS
- Implement HTMX for dynamic interactions
- Build forms, tables, detail views
- Generate navigation and layouts

**Generated Templates:**
```
frontend/
├── templates/
│   ├── base.html           # Base layout
│   ├── dashboard.html      # Main dashboard
│   ├── module_list.html    # List views
│   ├── module_form.html    # Create/Edit forms
│   └── module_detail.html  # Detail views
└── static/
    ├── css/
    └── js/
```

### QA Agent
**Responsibilities:**
- Generate comprehensive pytest tests
- Validate code for bugs and security issues
- Create test fixtures and mock data
- Provide code improvement suggestions
- Generate test coverage reports

**Generated Tests:**
```python
# Example test file
def test_create_product(db_session):
    product = Product(name="Test Product", sku="TEST-001")
    db_session.add(product)
    await db_session.commit()
    assert product.id is not None

def test_api_get_products(client):
    response = client.get("/products")
    assert response.status_code == 200
```

## 🔌 API Endpoints

### Project Management
```http
POST   /projects/create          # Create new project
GET    /projects                 # List all projects
GET    /projects/{id}            # Get project details
DELETE /projects/{id}            # Delete project
```

### Chat & Requirements
```http
POST   /chat                     # Chat with PM Agent
POST   /chat/generate-prd        # Generate PRD
POST   /upload                   # Upload document for RAG
```

### Code Generation
```http
POST   /agent/backend            # Generate backend code
POST   /agent/frontend           # Generate frontend code
POST   /agent/qa                 # Run QA tests
```

### File Management
```http
GET    /projects/{id}/files      # List project files
GET    /projects/{id}/file-tree  # Get file tree
GET    /projects/{id}/file       # Read file
POST   /projects/{id}/file       # Write file
```

### Preview
```http
GET    /preview/{id}/{path}      # Preview generated frontend
```

## 🛠️ Configuration

### LLM Providers

**OpenAI (Recommended)**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
DEFAULT_MODEL=gpt-4-turbo-preview
```

**Anthropic Claude**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
DEFAULT_MODEL=claude-3-opus-20240229
```

**Local LLM (llama.cpp)**
```env
LLM_PROVIDER=local
LOCAL_MODEL_PATH=./models/llama-2-7b.gguf
```

### Embeddings

**OpenAI Embeddings**
```env
EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_MODEL=text-embedding-3-small
```

**Local Embeddings**
```env
EMBEDDINGS_PROVIDER=local
# Uses sentence-transformers: all-MiniLM-L6-v2
```

## 📁 Project Structure

```
poc/
├── main.py                 # FastAPI application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
│
├── app/
│   ├── agents/           # AI agents
│   │   ├── pm_agent.py
│   │   ├── backend_agent.py
│   │   ├── frontend_agent.py
│   │   └── qa_agent.py
│   │
│   ├── services/         # Core services
│   │   ├── file_manager.py
│   │   ├── workspace.py
│   │   ├── llm_adapter.py
│   │   └── rag_service.py
│   │
│   ├── ingestion/        # Document processing
│   │   ├── parsers.py
│   │   └── embeddings.py
│   │
│   ├── templates/        # HTML templates
│   │   └── index.html
│   │
│   └── static/           # Static assets
│       ├── css/
│       └── js/
│
├── workspace/            # Generated projects
│   └── project_xxx/
│       ├── backend/
│       ├── frontend/
│       └── metadata.json
│
├── uploads/              # Uploaded documents
├── data/                 # Database & vector store
│   ├── chroma/          # ChromaDB
│   └── erp_builder.db   # SQLite
│
└── README.md
```

## 🧪 Testing Generated Code

### Run Backend Tests
```bash
cd workspace/project_xxx/backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

### Run Backend Server
```bash
cd workspace/project_xxx/backend

# Run FastAPI server
uvicorn app.main:app --reload

# API available at: http://localhost:8000
```

## 🔧 Troubleshooting

### Issue: Import errors
**Solution:** Ensure virtual environment is activated
```bash
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: LLM API errors
**Solution:** Check API keys in `.env`
```bash
# Verify API key is set
echo $env:OPENAI_API_KEY
```

### Issue: ChromaDB errors
**Solution:** Clear vector database
```bash
Remove-Item -Recurse -Force data/chroma
# Restart application
```

### Issue: Monaco editor not loading
**Solution:** Check internet connection (CDN required) or use local copy

## 📊 Performance Tips

1. **Use GPT-4 for complex ERPs** - Better code quality
2. **Start with smaller modules** - Iterate and expand
3. **Upload relevant documents** - Improves context understanding
4. **Review generated code** - Edit in Monaco editor
5. **Run QA early** - Catch issues before they compound

## 🔐 Security Considerations

- **API Keys**: Never commit `.env` to version control
- **Generated Code**: Review before deploying to production
- **Database**: Change default passwords in generated code
- **CORS**: Configure appropriately for production
- **Validation**: Generated code includes Pydantic validation

## 🚀 Deployment

### Local Development
```bash
python main.py
# Access: http://localhost:8000
```

### Production Deployment
```bash
# Use production WSGI server
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🤝 Contributing

This is a proof-of-concept system. Contributions welcome:
1. Improve agent prompts for better code generation
2. Add support for more document types
3. Enhance UI/UX
4. Add more LLM providers
5. Improve test generation

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- FastAPI - Modern web framework
- OpenAI - LLM capabilities
- ChromaDB - Vector database
- Monaco Editor - Code editor
- TailwindCSS - UI styling
- HTMX - Dynamic interactions

## 📞 Support

For issues and questions:
1. Check troubleshooting section
2. Review agent conversation logs
3. Examine generated code structure
4. Consult FastAPI/Jinja2 documentation

---

**Built with ❤️ for rapid ERP development**
