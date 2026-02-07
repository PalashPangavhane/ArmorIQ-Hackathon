"""
Configuration Settings Module

Central configuration for the ArmorIQ system.
"""

from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class RagSettings(BaseSettings):
    """RAG system configuration."""
    embedding_model: str = "text-embedding-ada-002"
    chunk_size: int = 512
    chunk_overlap: int = 50
    vector_db_url: str = "localhost:6333"
    collection_name: str = "financial_docs"


class GnnSettings(BaseSettings):
    """GNN risk model configuration."""
    model_path: str = "models/fraud_gnn.pt"
    risk_threshold_low: float = 0.3
    risk_threshold_medium: float = 0.6
    risk_threshold_high: float = 0.8


class PolicySettings(BaseSettings):
    """Policy engine configuration."""
    basic_approval_limit: float = 1000.0
    dual_approval_threshold: float = 10000.0
    ceo_agent_limit: float = 50000.0
    daily_ceo_limit: float = 200000.0


class Settings(BaseSettings):
    """Main application settings."""
    app_name: str = "ArmorIQ"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Component settings
    rag: RagSettings = RagSettings()
    gnn: GnnSettings = GnnSettings()
    policy: PolicySettings = PolicySettings()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


settings = Settings()
