from typing import Optional, List, Dict, Any
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMAdapter:
    """Unified interface for LLM providers (OpenAI, Anthropic, Gemini, Local)."""
    
    def __init__(
        self, 
        provider: str = "gemini",
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client."""
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        elif self.provider == "gemini":
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set for gemini provider")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
        
        elif self.provider == "local":
            from llama_cpp import Llama
            model_path = os.getenv("LOCAL_MODEL_PATH")
            if not model_path:
                raise ValueError("LOCAL_MODEL_PATH not set for local provider")
            self.client = Llama(model_path=model_path, n_ctx=4096)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Send chat messages and get response."""
        
        # Merge kwargs with defaults
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        if self.provider == "openai":
            return await self._chat_openai(messages, system_prompt, temperature, max_tokens)
        
        elif self.provider == "anthropic":
            return await self._chat_anthropic(messages, system_prompt, temperature, max_tokens)
        
        elif self.provider == "gemini":
            return await self._chat_gemini(messages, system_prompt, temperature, max_tokens)
        
        elif self.provider == "local":
            return await self._chat_local(messages, system_prompt, temperature, max_tokens)
    
    async def _chat_openai(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """OpenAI chat completion."""
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        formatted_messages.extend(messages)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    async def _chat_anthropic(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Anthropic (Claude) chat completion."""
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt or "",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.content[0].text
    
    async def _chat_gemini(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Google Gemini chat completion."""
        # Format messages into a single prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}\n")
        
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            prompt_parts.append(f"{role}: {content}\n")
        
        # Add final assistant prompt
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)
        
        # Configure generation
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        # Run synchronous Gemini call in thread pool to avoid blocking
        def _sync_generate():
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        
        # Execute in thread pool
        response_text = await asyncio.to_thread(_sync_generate)
        return response_text
    
    async def _chat_local(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Local LLM (llama.cpp) completion."""
        # Format messages into a single prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
        
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            prompt_parts.append(f"{role}: {content}")
        
        prompt_parts.append("Assistant:")
        prompt = "\n\n".join(prompt_parts)
        
        response = self.client(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["User:", "Human:"]
        )
        
        return response["choices"][0]["text"].strip()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Simple text generation."""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, **kwargs)
