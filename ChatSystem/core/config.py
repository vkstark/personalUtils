#!/usr/bin/env python3
"""
Configuration management using Pydantic Settings
Loads from .env and provides validated settings
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation"""

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Model Selection
    model_name: str = Field(default="gpt-4o", description="Default model to use")

    # Chat Settings
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream_responses: bool = Field(default=True)

    # Tool Settings
    enable_tools: bool = Field(default=True)
    parallel_tool_calls: bool = Field(default=False)

    # Agent Settings
    max_agent_iterations: int = Field(default=5, ge=1, le=20)
    enable_planning: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="chatsystem.log")

    # Config file path
    config_yaml_path: str = Field(default="config.yaml")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model name"""
        valid_models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4.1",
            "gpt-4.1-mini", "gpt-4.1-nano",
            "o3-mini", "o3", "gpt-5"
        ]
        if v not in valid_models:
            raise ValueError(f"Model must be one of: {', '.join(valid_models)}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    def load_yaml_config(self) -> Dict[str, Any]:
        """Load additional configuration from YAML"""
        yaml_path = Path(self.config_yaml_path)
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_model_for_task(self, task_type: str = "general") -> str:
        """Get optimal model for task type"""
        yaml_config = self.load_yaml_config()
        models = yaml_config.get("models", {})

        # Map task type to model
        return models.get(task_type, self.model_name)

    def get_enabled_tools(self) -> List[str]:
        """Get list of enabled tools from config"""
        if not self.enable_tools:
            return []

        yaml_config = self.load_yaml_config()
        tools_config = yaml_config.get("tools", {})
        return tools_config.get("enabled", [])

    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration"""
        yaml_config = self.load_yaml_config()
        agent_config = yaml_config.get("agent", {})

        return {
            "max_iterations": agent_config.get("max_iterations", self.max_agent_iterations),
            "enable_planning": agent_config.get("enable_planning", self.enable_planning),
            "enable_reasoning": agent_config.get("enable_reasoning", True),
            "timeout_seconds": agent_config.get("timeout_seconds", 300),
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Model pricing information (per 1M tokens)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},  # Estimated 26% cheaper
    "gpt-4.1-mini": {"input": 0.12, "output": 0.48},
    "gpt-4.1-nano": {"input": 0.08, "output": 0.32},
    "o3-mini": {"input": 1.00, "output": 4.00},
    "o3": {"input": 10.00, "output": 40.00},
    "gpt-5": {"input": 15.00, "output": 60.00},  # Estimated
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for API call"""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
