from typing import List, Dict, Optional
from app.services.llm_adapter import LLMAdapter
from app.services.rag_service import RAGService


class PMAgent:
    """Project Manager Agent - Collects requirements and generates PRD."""
    
    SYSTEM_PROMPT = """You are an expert ERP Project Manager specialized in gathering requirements for ERP systems.

Your responsibilities:
1. Ask clarifying questions about ERP modules, business processes, user roles, and data entities
2. Focus ONLY on ERP-related systems (Inventory, Sales, HR, Finance, Manufacturing, etc.)
3. Gather complete requirements before generating PRD
4. Generate a comprehensive Product Requirements Document (PRD)

Key areas to explore:
- Business modules needed (e.g., Inventory Management, Order Processing, HR Management)
- User roles and permissions
- Database entities and relationships
- Business workflows and processes
- Reporting and analytics needs
- Integration requirements

Always ask one or two questions at a time. Be conversational but professional.
When the user confirms requirements are complete, generate a structured PRD."""
    
    def __init__(self, llm_adapter: LLMAdapter, rag_service: RAGService):
        self.llm = llm_adapter
        self.rag = rag_service
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.project_requirements: Dict[str, Dict] = {}
    
    async def chat(
        self, 
        project_id: str, 
        user_message: str,
        include_context: bool = True
    ) -> Dict[str, any]:
        """Handle chat interaction with the PM agent."""
        
        # Initialize conversation if needed
        if project_id not in self.conversation_history:
            self.conversation_history[project_id] = []
            self.project_requirements[project_id] = {
                "modules": [],
                "roles": [],
                "entities": [],
                "workflows": []
            }
        
        # Get relevant context from uploaded documents
        context = ""
        if include_context:
            context = self.rag.get_context_for_query(user_message, project_id)
        
        # Add user message to history
        self.conversation_history[project_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare enhanced prompt with context
        enhanced_message = user_message
        if context:
            enhanced_message = f"Context from uploaded documents:\n{context}\n\nUser: {user_message}"
        
        # Update the last message with enhanced version
        self.conversation_history[project_id][-1]["content"] = enhanced_message
        
        # Get response from LLM
        response = await self.llm.chat(
            messages=self.conversation_history[project_id],
            system_prompt=self.SYSTEM_PROMPT
        )
        
        # Add assistant response to history
        self.conversation_history[project_id].append({
            "role": "assistant",
            "content": response
        })
        
        # Check if this is a PRD generation request
        is_prd = any(keyword in user_message.lower() for keyword in [
            "generate prd", "create prd", "finalize requirements", "ready to generate"
        ])
        
        return {
            "message": response,
            "is_prd": is_prd,
            "project_id": project_id
        }
    
    async def generate_prd(self, project_id: str) -> Dict[str, any]:
        """Generate a structured PRD from the conversation."""
        
        if project_id not in self.conversation_history:
            return {"error": "No conversation history found"}
        
        prd_prompt = """Based on our conversation, generate a comprehensive Product Requirements Document (PRD) for this ERP system.

Format the PRD as a JSON object with the following structure:
{
  "project_name": "string",
  "overview": "string - brief description",
  "modules": [
    {
      "name": "string",
      "description": "string",
      "features": ["list of features"]
    }
  ],
  "entities": [
    {
      "name": "string",
      "description": "string",
      "fields": [
        {
          "name": "string",
          "type": "string (e.g., string, integer, date, foreign_key)",
          "required": boolean
        }
      ]
    }
  ],
  "roles": [
    {
      "name": "string",
      "permissions": ["list of permissions"]
    }
  ],
  "workflows": [
    {
      "name": "string",
      "steps": ["list of steps"]
    }
  ]
}

Generate ONLY the JSON, no additional text."""
        
        messages = self.conversation_history[project_id].copy()
        messages.append({"role": "user", "content": prd_prompt})
        
        prd_response = await self.llm.chat(
            messages=messages,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3  # Lower temperature for structured output
        )
        
        # Parse JSON response
        import json
        try:
            # Clean response if it contains markdown
            cleaned = prd_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            prd = json.loads(cleaned.strip())
            
            return {
                "success": True,
                "prd": prd,
                "project_id": project_id
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse PRD: {str(e)}",
                "raw_response": prd_response
            }
    
    def reset_conversation(self, project_id: str) -> None:
        """Reset conversation history for a project."""
        if project_id in self.conversation_history:
            del self.conversation_history[project_id]
        if project_id in self.project_requirements:
            del self.project_requirements[project_id]
