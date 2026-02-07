"""
Local LLM Client for Qwen3 8B

Connects to locally running Qwen3 8B (4-bit quantized) via Ollama API.
Used for intelligent expense validation without external APIs.

SETUP:
1. Install Ollama: https://ollama.ai
2. Pull model: ollama pull qwen3:8b
3. Run model: ollama serve (runs on localhost:11434)
"""

import asyncio
import json
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


@dataclass
class LLMResponse:
    """Response from local LLM."""
    content: str
    model: str
    tokens_used: int
    thinking: Optional[str] = None  # For Qwen3's thinking mode


class LocalLLMClient:
    """
    Client for locally-run LLMs via Ollama.
    
    Supports Qwen3 8B with thinking mode enabled for
    better reasoning on expense validation tasks.
    """
    
    def __init__(
        self, 
        model: str = "qwen3:8b",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        enable_thinking: bool = True
    ) -> LLMResponse:
        """
        Generate response from local LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Creativity (0.0-1.0)
            max_tokens: Max response length
            enable_thinking: Enable Qwen3's thinking mode
            
        Returns:
            LLMResponse with content and metadata
        """
        client = await self._get_client()
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add thinking instruction for Qwen3
        if enable_thinking:
            prompt = f"{prompt}\n\n/think"
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "")
            
            # Parse thinking vs answer for Qwen3
            thinking = None
            if "<think>" in content and "</think>" in content:
                think_start = content.find("<think>") + 7
                think_end = content.find("</think>")
                thinking = content[think_start:think_end].strip()
                content = content[think_end + 8:].strip()
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=data.get("eval_count", 0),
                thinking=thinking
            )
            
        except httpx.ConnectError:
            # Ollama not running - return helpful error
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Please start Ollama with: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")
    
    async def validate_expense(
        self,
        expense_type: str,
        amount: float,
        from_location: str,
        to_location: str,
        description: str,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Validate an expense claim using LLM reasoning.
        
        Args:
            expense_type: Type of expense (cab, flight, hotel, food)
            amount: Claimed amount
            from_location: Origin
            to_location: Destination
            description: Expense description
            currency: Currency code
            
        Returns:
            Dict with validation result and reasoning
        """
        system_prompt = """You are an expense validation AI. Your job is to check if expense claims are reasonable.

You have knowledge of:
- Typical travel costs in major Indian cities
- Average cab fares: ₹15-25 per km in cities
- Airport/station distances from city centers
- Reasonable meal costs, hotel rates, etc.

For each expense, determine:
1. Is the amount reasonable for the claimed service?
2. What would be the expected cost range?
3. Should this be APPROVED, FLAGGED for review, or REJECTED?

Always respond in JSON format:
{
  "decision": "APPROVE" | "FLAG" | "REJECT",
  "expected_range": {"min": X, "max": Y},
  "reasoning": "explanation",
  "confidence": 0.0-1.0
}"""

        prompt = f"""Validate this expense claim:

Type: {expense_type}
Amount Claimed: {currency} {amount}
From: {from_location}
To: {to_location}
Description: {description}

Is this amount reasonable? Provide your analysis in JSON format."""

        try:
            response = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower for more consistent validation
                enable_thinking=True
            )
            
            # Parse JSON from response
            content = response.content
            
            # Try to extract JSON
            try:
                # Find JSON in response
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                    result["thinking"] = response.thinking
                    result["raw_response"] = content
                    return result
            except json.JSONDecodeError:
                pass
            
            # Fallback: return raw response
            return {
                "decision": "FLAG",
                "reasoning": content,
                "thinking": response.thinking,
                "error": "Could not parse structured response"
            }
            
        except ConnectionError as e:
            # Ollama not running - use fallback heuristics
            return self._fallback_validation(expense_type, amount, from_location, to_location)
        except Exception as e:
            return {
                "decision": "FLAG",
                "reasoning": f"Validation error: {str(e)}",
                "error": str(e)
            }
    
    def _fallback_validation(
        self,
        expense_type: str,
        amount: float,
        from_location: str,
        to_location: str
    ) -> Dict[str, Any]:
        """
        Fallback validation when LLM is unavailable.
        Uses simple heuristics.
        """
        # Simple heuristics for Indian cities
        cab_rates = {
            "airport": (500, 1500),  # Airport transfers
            "local": (100, 500),      # Within city
            "intercity": (1000, 5000) # Between cities
        }
        
        # Detect trip type
        trip_type = "local"
        lower_from = from_location.lower()
        lower_to = to_location.lower()
        
        if "airport" in lower_from or "airport" in lower_to:
            trip_type = "airport"
        elif any(city in lower_to for city in ["mumbai", "delhi", "bangalore", "hyderabad", "chennai", "pune"]):
            if any(city in lower_from for city in ["mumbai", "delhi", "bangalore", "hyderabad", "chennai", "pune"]):
                if lower_from != lower_to:
                    trip_type = "intercity"
        
        min_expected, max_expected = cab_rates.get(trip_type, (100, 1000))
        
        if amount <= max_expected * 1.2:  # 20% tolerance
            decision = "APPROVE"
        elif amount <= max_expected * 2:
            decision = "FLAG"
        else:
            decision = "REJECT"
        
        return {
            "decision": decision,
            "expected_range": {"min": min_expected, "max": max_expected},
            "reasoning": f"[Fallback mode] {trip_type.title()} trip typically costs ₹{min_expected}-{max_expected}",
            "confidence": 0.6,
            "fallback_mode": True
        }
    
    async def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
            return False
        except:
            return False


# Convenience function for quick validation
async def validate_cab_expense(
    amount: float,
    from_location: str,
    to_location: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    Quick function to validate a cab expense.
    
    Example:
        result = await validate_cab_expense(
            amount=850,
            from_location="Hinjewadi IT Park, Pune",
            to_location="Pune Airport"
        )
    """
    client = LocalLLMClient()
    try:
        return await client.validate_expense(
            expense_type="cab",
            amount=amount,
            from_location=from_location,
            to_location=to_location,
            description=description
        )
    finally:
        await client.close()
