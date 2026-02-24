"""
Pramana AI - Configuration
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# Base directory for the sidecar
BASE_DIR = Path(__file__).parent.resolve()
ROOT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    """Application settings"""
    
    # App Info
    app_name: str = "Pramana AI"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # Paths
    data_root: Path = ROOT_DIR / "data"
    cases_dir: Path = ROOT_DIR / "data/demo"
    policies_dir: Path = ROOT_DIR / "data/policies"
    demo_dir: Path = ROOT_DIR / "data/demo"
    outputs_dir: Path = ROOT_DIR / "data/outputs"
    
    # Database
    db_path: Path = ROOT_DIR / "data/pramana.sqlite"
    
    # Ollama Configuration (Edge AI - Strict Local)
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "MedAIBase/MedGemma1.5:4b"  # HAI-DEF model for clinical reasoning
    embedding_model: str = "nomic-embed-text"
    
    # API Settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    model_config = SettingsConfigDict(
        env_prefix="PRAMANA_",
        env_file=".env",
        extra="ignore"
    )


settings = Settings()

