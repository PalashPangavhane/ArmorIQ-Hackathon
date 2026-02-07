"""
Gemini LLM Service Module

Provides LLM capabilities using Google Gemini for agent reasoning.
"""

import os
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types


class GeminiLLMService:
    """LLM service using Google Gemini for agent reasoning."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self._client = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the Gemini client."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self._client = genai.Client(api_key=api_key)
        self._initialized = True
    
    async def generate(
        self, 
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        if not self._initialized:
            self.initialize()
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction
        )
        
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        
        return response.text
    
    async def analyze_request(
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
        prompt = f"""Analyze this payment request and provide a recommendation.

REQUEST DETAILS:
- Request ID: {request.get('request_id')}
- Employee: {request.get('employee_id')}
- Amount: ${request.get('amount', 0):.2f}
- Department: {request.get('department')}
- Purpose: {request.get('purpose')}
- Category: {request.get('category')}

CONTEXT:
{self._format_context(context)}

Provide your analysis in the following JSON format:
{{
    "recommendation": "APPROVE" | "REJECT" | "ESCALATE" | "FLAG",
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "risk_factors": ["factor1", "factor2"],
    "suggested_constraints": []
}}
"""
        
        system_instruction = """You are a financial analysis AI agent. 
Your role is to analyze payment requests and provide recommendations.
You must be thorough, fair, and security-conscious.
Always explain your reasoning clearly.
Respond only with valid JSON."""
        
        response = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.3
        )
        
        # Parse JSON response
        try:
            import json
            # Clean response if needed
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {
                "recommendation": "ESCALATE",
                "confidence": 0.5,
                "reasoning": "Unable to parse LLM response, escalating for human review",
                "risk_factors": ["parsing_error"],
                "suggested_constraints": [],
                "raw_response": response
            }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt."""
        parts = []
        
        if context.get("budget_context"):
            parts.append(f"Budget Info: {context['budget_context']}")
        
        if context.get("spending_history"):
            parts.append(f"Spending History: {context['spending_history']}")
        
        if context.get("vendor_context"):
            parts.append(f"Vendor Info: {context['vendor_context']}")
        
        if context.get("risk_signal"):
            risk = context["risk_signal"]
            parts.append(f"Risk Level: {risk.get('risk_level', 'UNKNOWN')}")
            parts.append(f"Risk Score: {risk.get('risk_score', 'N/A')}")
            if risk.get("risk_reasons"):
                parts.append(f"Risk Factors: {', '.join(risk['risk_reasons'])}")
        
        return "\n".join(parts) if parts else "No additional context available"


# Singleton instance
_llm_service: Optional[GeminiLLMService] = None


def get_llm_service() -> GeminiLLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = GeminiLLMService()
    return _llm_service
