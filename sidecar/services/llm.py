"""
LLM Service - Hybrid HuggingFace API + Ollama Backend
Automatically selects best available backend for inference
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    backend: str  # "huggingface" or "ollama"
    tokens_used: Optional[int] = None


class LLMService:
    """
    Hybrid LLM service that uses HuggingFace API when online,
    falls back to Ollama when offline or HF unavailable
    """
    
    def __init__(self):
        self._ollama_available = False
        self._init_backends()
    
    def _init_backends(self):
        """Initialize available backends"""
        # Try Ollama (Local Edge Inference)
        try:
            import ollama
            ollama.list()  # Test connection
            self._ollama_available = True
            logger.info("Ollama backend initialized (Edge Mode)")
        except Exception as e:
            logger.warning(f"Ollama init failed: {e}")
    
    @property
    def available_backends(self) -> List[str]:
        """List available backends"""
        backends = []
        if self._ollama_available:
            backends.append("ollama")
        return backends
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Send chat completion request to the local Ollama backend
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            json_mode: Force JSON format output from the model
        """
        # Add system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Strictly local Ollama execution for Edge AI compliance
        return await self._chat_ollama(messages, max_tokens, temperature, json_mode)
    
    async def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        json_mode: bool = False
    ) -> LLMResponse:
        """Chat using local Ollama"""
        import ollama
        
        try:
            kwargs = {
                "model": settings.default_model,
                "messages": messages,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            if json_mode:
                kwargs["format"] = "json"
                
            response = ollama.chat(**kwargs)
            
            content = response["message"]["content"]
            
            return LLMResponse(
                content=content,
                model=settings.default_model,
                backend="ollama",
                tokens_used=response.get("eval_count")
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Generate JSON response from LLM"""
        import json
        
        json_system = (system_prompt or "") + "\nRespond with valid JSON only, no markdown."
        
        response = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=json_system,
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temp for JSON
            json_mode=True
        )
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Architectural Fallback: Force extraction of only the JSON block 
        # to safely slice out any <unused94>thought tags from Pramana AI
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            content = content[start_idx:end_idx+1]
            
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {content[:200]}")
            return {"error": "Failed to parse response", "raw": content[:500]}


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
