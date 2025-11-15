from typing import Dict, List
from app.services.llm_adapter import LLMAdapter
from app.services.file_manager import FileManager


class QAAgent:
    """QA Agent - Generates tests and validates generated code."""
    
    SYSTEM_PROMPT = """You are an expert QA engineer specialized in testing ERP systems.

Your responsibilities:
1. Generate comprehensive pytest tests for backend code
2. Validate code structure and best practices
3. Check for common bugs and security issues
4. Generate test data and fixtures
5. Report bugs with clear descriptions and suggested fixes

Test coverage areas:
- Unit tests for models and services
- Integration tests for API endpoints
- Test data fixtures
- Edge cases and error handling

Generate production-ready tests with proper assertions and coverage."""
    
    def __init__(self, llm_adapter: LLMAdapter, file_manager: FileManager):
        self.llm = llm_adapter
        self.file_manager = file_manager
    
    async def run_qa(self, project_id: str, prd: Dict) -> Dict[str, any]:
        """Run QA process on generated code."""
        
        try:
            results = {
                "tests_generated": await self._generate_tests(project_id, prd),
                "code_validation": await self._validate_code(project_id, prd),
                "test_fixtures": await self._generate_fixtures(project_id, prd)
            }
            
            return {
                "success": True,
                "project_id": project_id,
                "qa_results": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_tests(self, project_id: str, prd: Dict) -> List[str]:
        """Generate pytest tests for the backend."""
        files_created = []
        
        entities = prd.get("entities", [])
        
        # Generate conftest.py
        conftest = """import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
"""
        
        self.file_manager.write_file(project_id, "backend/tests/conftest.py", conftest)
        files_created.append("backend/tests/conftest.py")
        
        # Generate tests for each entity
        for entity in entities:
            prompt = f"""Generate comprehensive pytest tests for this entity:

Entity: {entity['name']}
Fields: {entity.get('fields', [])}

Include tests for:
1. Creating a new {entity['name']}
2. Reading/fetching {entity['name']}
3. Updating {entity['name']}
4. Deleting {entity['name']}
5. Validation errors
6. Edge cases

Use pytest-asyncio and proper fixtures.
Generate ONLY the Python test code."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/tests/test_{entity['name'].lower()}.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        # Generate API endpoint tests
        modules = prd.get("modules", [])
        for module in modules:
            prompt = f"""Generate pytest tests for this API module:

Module: {module['name']}
Features: {module.get('features', [])}

Test all CRUD endpoints:
- GET /{module['name'].lower()}
- GET /{module['name'].lower()}/{{id}}
- POST /{module['name'].lower()}
- PUT /{module['name'].lower()}/{{id}}
- DELETE /{module['name'].lower()}/{{id}}

Include authentication, authorization, and error cases.
Generate ONLY the Python test code."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/tests/test_{module['name'].lower().replace(' ', '_')}_api.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        return files_created
    
    async def _validate_code(self, project_id: str, prd: Dict) -> Dict[str, any]:
        """Validate generated backend code."""
        
        # Read generated files
        backend_files = self.file_manager.list_files(project_id, "backend/app")
        
        issues = []
        suggestions = []
        
        for file_info in backend_files[:5]:  # Check first 5 files as sample
            file_path = file_info['path']
            content = self.file_manager.read_file(project_id, file_path)
            
            if not content:
                continue
            
            prompt = f"""Review this Python code for an ERP system and identify:

1. Potential bugs
2. Security issues
3. Best practice violations
4. Performance concerns
5. Missing error handling

Code file: {file_path}

```python
{content[:2000]}  # First 2000 chars
```

Provide a JSON response with:
{{
  "issues": ["list of critical issues"],
  "suggestions": ["list of improvements"]
}}

Generate ONLY the JSON, no additional text."""
            
            try:
                response = await self.llm.generate(prompt, temperature=0.3)
                import json
                
                # Clean and parse response
                cleaned = response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                
                result = json.loads(cleaned.strip())
                
                issues.extend([f"{file_path}: {issue}" for issue in result.get("issues", [])])
                suggestions.extend([f"{file_path}: {sugg}" for sugg in result.get("suggestions", [])])
            
            except Exception as e:
                issues.append(f"Failed to analyze {file_path}: {str(e)}")
        
        return {
            "files_checked": len(backend_files[:5]),
            "total_issues": len(issues),
            "total_suggestions": len(suggestions),
            "issues": issues,
            "suggestions": suggestions
        }
    
    async def _generate_fixtures(self, project_id: str, prd: Dict) -> List[str]:
        """Generate test data fixtures."""
        files_created = []
        
        entities = prd.get("entities", [])
        
        for entity in entities:
            prompt = f"""Generate test data fixtures for this entity:

Entity: {entity['name']}
Fields: {entity.get('fields', [])}

Create a Python file with:
1. Factory functions to create test instances
2. Sample data dictionaries
3. Edge case data (empty, invalid, boundary values)

Use Faker library for realistic data.
Generate ONLY the Python code."""
            
            code = await self.llm.generate(prompt, temperature=0.3)
            code = self._clean_code(code)
            
            filename = f"backend/tests/fixtures/{entity['name'].lower()}_fixtures.py"
            self.file_manager.write_file(project_id, filename, code)
            files_created.append(filename)
        
        return files_created
    
    def _clean_code(self, code: str) -> str:
        """Clean generated code."""
        cleaned = code.strip()
        if cleaned.startswith("```python"):
            cleaned = cleaned[9:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return cleaned.strip()
