"""
Entity Extractor Module

Uses LLM (Qwen3) to extract entities and relationships from documents
for building knowledge graphs. This is a core component of GraphRAG.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class EntityType(Enum):
    """Types of entities relevant to financial/payment domain."""
    PERSON = "person"
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    VENDOR = "vendor"
    POLICY = "policy"
    BUDGET = "budget"
    EXPENSE = "expense"
    APPROVAL = "approval"
    AMOUNT = "amount"
    DATE = "date"
    CATEGORY = "category"
    ROLE = "role"
    LOCATION = "location"
    DOCUMENT = "document"
    THRESHOLD = "threshold"
    PROCESS = "process"
    RULE = "rule"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Represents an extracted entity."""
    id: str
    name: str
    entity_type: EntityType
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    source_chunk_id: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "source_chunk_id": self.source_chunk_id,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data.get("type", "unknown")),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            source_chunk_id=data.get("source_chunk_id", ""),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class Relationship:
    """Represents a relationship between two entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    source_chunk_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source_entity_id,
            "target": self.target_entity_id,
            "type": self.relationship_type,
            "description": self.description,
            "properties": self.properties,
            "weight": self.weight,
            "source_chunk_id": self.source_chunk_id
        }


class EntityExtractor:
    """
    Extracts entities and relationships from text using LLM.
    
    This is a key component of GraphRAG that transforms unstructured
    text into structured knowledge graph elements.
    """
    
    # Predefined relationship types for financial domain
    RELATIONSHIP_TYPES = [
        "APPROVES", "APPROVED_BY", "BELONGS_TO", "MANAGES",
        "HAS_BUDGET", "SPENT_ON", "VENDOR_FOR", "REQUIRES",
        "REPORTS_TO", "OWNS", "LIMITS", "EXCEEDS", "COMPLIES_WITH",
        "VIOLATES", "RELATED_TO", "PART_OF", "CONTAINS", "REFERENCES"
    ]
    
    def __init__(
        self,
        llm_service=None,
        batch_size: int = 5,
        max_entities_per_chunk: int = 20,
        max_relationships_per_chunk: int = 30
    ):
        """
        Initialize entity extractor.
        
        Args:
            llm_service: LLM service for extraction (defaults to Ollama/Qwen)
            batch_size: Number of chunks to process in batch
            max_entities_per_chunk: Maximum entities to extract per chunk
            max_relationships_per_chunk: Maximum relationships per chunk
        """
        self.llm_service = llm_service
        self.batch_size = batch_size
        self.max_entities = max_entities_per_chunk
        self.max_relationships = max_relationships_per_chunk
        self._entity_cache: Dict[str, Entity] = {}
    
    def _ensure_llm(self):
        """Ensure LLM service is initialized."""
        if self.llm_service is None:
            from ..llm.ollama_service import OllamaLLMService
            self.llm_service = OllamaLLMService(model_name="qwen3:8b")
            self.llm_service.initialize()
    
    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """Generate deterministic ID for entity."""
        key = f"{entity_type}:{name.lower().strip()}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def _generate_relationship_id(self, source: str, target: str, rel_type: str) -> str:
        """Generate deterministic ID for relationship."""
        key = f"{source}:{rel_type}:{target}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def extract_from_text(
        self,
        text: str,
        chunk_id: str = "",
        context: Optional[str] = None
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from text.
        
        Args:
            text: Source text to extract from
            chunk_id: ID of the source chunk
            context: Optional context to help extraction
            
        Returns:
            Tuple of (entities, relationships)
        """
        self._ensure_llm()
        
        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, context)
        
        # Get LLM response
        response = self.llm_service.generate(
            prompt=prompt,
            system_instruction=self._get_system_prompt(),
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=2048
        )
        
        # Parse response
        entities, relationships = self._parse_extraction_response(response, chunk_id)
        
        return entities, relationships
    
    def extract_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from multiple chunks.
        
        Args:
            chunks: List of chunk dicts with 'content' and 'chunk_id'
            show_progress: Whether to show progress
            
        Returns:
            Tuple of (all_entities, all_relationships)
        """
        all_entities = []
        all_relationships = []
        
        for i, chunk in enumerate(chunks):
            if show_progress:
                print(f"  Extracting from chunk {i+1}/{len(chunks)}...", end="\r")
            
            content = chunk.get("content", "")
            chunk_id = chunk.get("chunk_id", f"chunk_{i}")
            
            entities, relationships = self.extract_from_text(content, chunk_id)
            
            # Deduplicate entities
            for entity in entities:
                if entity.id not in self._entity_cache:
                    self._entity_cache[entity.id] = entity
                    all_entities.append(entity)
            
            all_relationships.extend(relationships)
        
        if show_progress:
            print(f"  Extracted {len(all_entities)} entities, {len(all_relationships)} relationships")
        
        return all_entities, all_relationships
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for entity extraction."""
        return """You are an expert at extracting structured information from financial and business documents.
Your task is to identify entities (people, organizations, policies, amounts, etc.) and their relationships.

For the FINANCIAL DOMAIN, focus on:
- People: employees, managers, approvers
- Organizations: departments, vendors, companies
- Policies: expense policies, approval thresholds, compliance rules
- Financial: budgets, amounts, limits, expenses
- Processes: approvals, reimbursements, audits

Extract entities and relationships in the EXACT JSON format specified.
Be thorough but precise - only extract what is clearly stated or strongly implied."""

    def _build_extraction_prompt(self, text: str, context: Optional[str] = None) -> str:
        """Build the extraction prompt."""
        entity_types = ", ".join([t.value for t in EntityType])
        rel_types = ", ".join(self.RELATIONSHIP_TYPES)
        
        prompt = f"""Extract entities and relationships from the following text.

TEXT:
{text}

{f"CONTEXT: {context}" if context else ""}

ENTITY TYPES: {entity_types}
RELATIONSHIP TYPES: {rel_types}

Respond with ONLY a valid JSON object in this exact format:
{{
    "entities": [
        {{
            "name": "Entity Name",
            "type": "entity_type",
            "description": "Brief description",
            "properties": {{"key": "value"}}
        }}
    ],
    "relationships": [
        {{
            "source": "Source Entity Name",
            "target": "Target Entity Name",
            "type": "RELATIONSHIP_TYPE",
            "description": "Brief description"
        }}
    ]
}}

Extract up to {self.max_entities} entities and {self.max_relationships} relationships.
Focus on the most important entities and their key relationships."""
        
        return prompt
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and fix common JSON formatting issues from LLM output."""
        # Remove any thinking/reasoning blocks (Qwen3 uses <think> tags)
        import re
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'<\|think\|>.*?<\|/think\|>', '', response, flags=re.DOTALL)
        
        # Handle markdown code blocks
        if "```json" in response:
            parts = response.split("```json")
            if len(parts) > 1:
                response = parts[1].split("```")[0]
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                response = parts[1].split("```")[0] if "```" in parts[1] else parts[1]
        
        # Clean up common issues
        response = response.strip()
        
        # Fix trailing commas (common LLM error)
        response = re.sub(r',(\s*[}\]])', r'\1', response)
        
        # Fix unquoted keys (if any)
        response = re.sub(r'(\{|\,)\s*(\w+)\s*:', r'\1"\2":', response)
        
        return response
    
    def _parse_extraction_response(
        self,
        response: str,
        chunk_id: str
    ) -> Tuple[List[Entity], List[Relationship]]:
        """Parse the LLM response into entities and relationships."""
        entities = []
        relationships = []
        
        try:
            # Clean response
            cleaned = self._clean_json_response(response)
            
            # Find JSON object
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if not json_match:
                # Fallback to simple extraction
                return self.extract_entities_simple(response), []
            
            json_str = json_match.group()
            
            # Try to parse JSON
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try fixing more issues
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control chars
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"  Warning: JSON parse failed: {e}")
                    return self.extract_entities_simple(response), []
            
            # Parse entities
            for ent_data in data.get("entities", []):
                try:
                    entity_type = EntityType(ent_data.get("type", "unknown").lower())
                except ValueError:
                    entity_type = EntityType.UNKNOWN
                
                entity = Entity(
                    id=self._generate_entity_id(ent_data["name"], entity_type.value),
                    name=ent_data["name"],
                    entity_type=entity_type,
                    description=ent_data.get("description", ""),
                    properties=ent_data.get("properties", {}),
                    source_chunk_id=chunk_id
                )
                entities.append(entity)
            
            # Build entity name to ID mapping
            entity_map = {e.name.lower(): e.id for e in entities}
            entity_map.update({e.name: e.id for e in entities})
            
            # Also check cache
            for name, ent in self._entity_cache.items():
                entity_map[ent.name.lower()] = ent.id
                entity_map[ent.name] = ent.id
            
            # Parse relationships
            for rel_data in data.get("relationships", []):
                source_name = rel_data.get("source", "")
                target_name = rel_data.get("target", "")
                
                # Find entity IDs
                source_id = entity_map.get(source_name.lower()) or entity_map.get(source_name)
                target_id = entity_map.get(target_name.lower()) or entity_map.get(target_name)
                
                if source_id and target_id:
                    rel_type = rel_data.get("type", "RELATED_TO").upper()
                    if rel_type not in self.RELATIONSHIP_TYPES:
                        rel_type = "RELATED_TO"
                    
                    relationship = Relationship(
                        id=self._generate_relationship_id(source_id, target_id, rel_type),
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        relationship_type=rel_type,
                        description=rel_data.get("description", ""),
                        source_chunk_id=chunk_id
                    )
                    relationships.append(relationship)
        
        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse extraction response: {e}")
        except Exception as e:
            print(f"  Warning: Error during extraction: {e}")
        
        return entities, relationships
    
    def extract_entities_simple(self, text: str) -> List[Entity]:
        """
        Simple entity extraction without relationships.
        Uses pattern matching for common financial entities.
        """
        entities = []
        
        # Dollar amounts
        amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)
        for amt in amounts:
            entities.append(Entity(
                id=self._generate_entity_id(amt, "amount"),
                name=amt,
                entity_type=EntityType.AMOUNT,
                properties={"value": amt}
            ))
        
        # Percentages
        percentages = re.findall(r'\d+(?:\.\d+)?%', text)
        for pct in percentages:
            entities.append(Entity(
                id=self._generate_entity_id(pct, "amount"),
                name=pct,
                entity_type=EntityType.AMOUNT,
                properties={"value": pct, "is_percentage": True}
            ))
        
        # Dates
        dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', text)
        for date in dates:
            entities.append(Entity(
                id=self._generate_entity_id(date, "date"),
                name=date,
                entity_type=EntityType.DATE
            ))
        
        return entities
    
    def clear_cache(self):
        """Clear the entity cache."""
        self._entity_cache.clear()
