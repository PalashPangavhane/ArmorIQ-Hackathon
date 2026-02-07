"""
Ollama LLM Service Module

Provides LLM capabilities using Ollama for local agent reasoning with Qwen 3.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


class OllamaLLMService:
    """LLM service using Ollama for local agent reasoning."""
    
    def __init__(
        self, 
        model_name: str = None,
        base_url: str = None
    ):
        self.model_name = model_name or os.environ.get("OLLAMA_LLM_MODEL", "qwen3:8b-q4_K_M")
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._initialized = False
    
    def initialize(self):
        """Initialize the Ollama client and verify model availability."""
        # Check if Ollama is running
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Ollama is not responding properly")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Ollama is not running. Start it with: ollama serve"
            )
        
        # Check if model is available
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        
        # Check for exact match or base name match
        model_found = any(
            self.model_name in name or name.startswith(self.model_name.split(":")[0])
            for name in model_names
        )
        
        if not model_found:
            print(f"Model {self.model_name} not found. Available models: {model_names}")
            print(f"Pulling model {self.model_name}...")
            # Model will be pulled on first use
        
        self._initialized = True
        print(f"Ollama LLM service initialized with model: {self.model_name}")
    
    def generate(
        self, 
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Generated text response
        """
        if not self._initialized:
            self.initialize()
        
        # Build the request
        request_data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_instruction:
            request_data["system"] = system_instruction
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=request_data,
            timeout=120
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"LLM request failed: {response.text}")
        
        return response.json()["response"]
    
    async def generate_async(
        self, 
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Async wrapper for generate (uses sync under the hood).
        
        Args:
            prompt: User prompt
            system_instruction: Optional system instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        return self.generate(prompt, system_instruction, temperature, max_tokens)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Chat completion with message history.
        
        Args:
            messages: List of messages with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        if not self._initialized:
            self.initialize()
        
        request_data = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=request_data,
            timeout=120
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Chat request failed: {response.text}")
        
        return response.json()["message"]["content"]
    
    def analyze_request(
        self,
        request: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a payment/reimbursement request.
        
        Args:
            request: The payment request details
            context: Additional context (budget, history, etc.)
            
        Returns:
            Analysis results with recommendation
        """
        system_instruction = """You are a financial analysis AI assistant. Analyze payment and expense requests 
based on company policies, budget constraints, and historical patterns. Provide clear recommendations 
with detailed reasoning. Always respond in valid JSON format."""

        prompt = f"""Analyze this payment request and provide a recommendation.

REQUEST DETAILS:
- Request ID: {request.get('request_id', 'N/A')}
- Employee: {request.get('employee_id', 'N/A')}
- Amount: ${request.get('amount', 0):.2f}
- Department: {request.get('department', 'N/A')}
- Purpose: {request.get('purpose', 'N/A')}
- Category: {request.get('category', 'N/A')}
- Vendor: {request.get('vendor', 'N/A')}

CONTEXT:
{self._format_context(context)}

Analyze this request and respond with ONLY a valid JSON object in this exact format:
{{
    "recommendation": "APPROVE" or "REJECT" or "ESCALATE" or "FLAG",
    "confidence": <number between 0.0 and 1.0>,
    "reasoning": "<your detailed explanation>",
    "risk_factors": ["<factor1>", "<factor2>"],
    "suggested_constraints": ["<constraint1>", "<constraint2>"],
    "policy_compliance": true or false,
    "budget_impact": "<description of budget impact>"
}}"""

        response = self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1024
        )
        
        # Parse JSON response
        try:
            # Try to extract JSON from response
            response_text = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Return a structured error response
            return {
                "recommendation": "ESCALATE",
                "confidence": 0.0,
                "reasoning": f"Failed to parse LLM response: {response[:200]}",
                "risk_factors": ["parsing_error"],
                "suggested_constraints": [],
                "policy_compliance": None,
                "budget_impact": "Unknown"
            }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary for prompt."""
        formatted_parts = []
        
        if "budget" in context:
            budget = context["budget"]
            formatted_parts.append(f"""BUDGET INFORMATION:
- Department Budget: ${budget.get('total', 0):,.2f}
- Spent YTD: ${budget.get('spent', 0):,.2f}
- Remaining: ${budget.get('remaining', 0):,.2f}
- Utilization: {budget.get('utilization', 0):.1f}%""")
        
        if "policy" in context:
            formatted_parts.append(f"""RELEVANT POLICIES:
{context['policy']}""")
        
        if "vendor" in context:
            vendor = context["vendor"]
            formatted_parts.append(f"""VENDOR INFORMATION:
- Vendor: {vendor.get('name', 'Unknown')}
- Status: {vendor.get('status', 'Unknown')}
- Risk Level: {vendor.get('risk', 'Unknown')}
- Preferred: {vendor.get('preferred', False)}""")
        
        if "history" in context:
            formatted_parts.append(f"""SPENDING HISTORY:
{context['history']}""")
        
        return "\n\n".join(formatted_parts) if formatted_parts else "No additional context provided."
    
    def summarize_documents(self, documents: List[str], query: str) -> str:
        """
        Summarize retrieved documents relevant to a query.
        
        Args:
            documents: List of document contents
            query: The original query
            
        Returns:
            Summarized response
        """
        combined_docs = "\n\n---\n\n".join(documents[:5])  # Limit to 5 docs
        
        prompt = f"""Based on the following documents, answer the query.

QUERY: {query}

DOCUMENTS:
{combined_docs}

Provide a clear, concise answer based only on the information in the documents above."""

        return self.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=1024
        )


# Convenience function to get a singleton instance
_ollama_service = None

def get_ollama_service(model_name: str = "qwen3:8b") -> OllamaLLMService:
    """Get or create a singleton Ollama LLM service instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaLLMService(model_name=model_name)
    return _ollama_service
