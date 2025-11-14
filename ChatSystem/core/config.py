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
    """
    Manages application settings using Pydantic for validation.

    Loads configuration from environment variables, a .env file, and a specified
    YAML file. Provides a centralized and validated source for all configuration
    parameters.

    Attributes:
        openai_api_key (str): The API key for OpenAI services.
        model_name (str): The default GPT model to be used for chat.
        max_tokens (int): The maximum number of tokens for a chat completion.
        temperature (float): The sampling temperature for generating responses.
        stream_responses (bool): Whether to stream chat responses.
        enable_tools (bool): Flag to enable or disable function calling tools.
        parallel_tool_calls (bool): Flag to enable parallel tool execution.
        max_agent_iterations (int): The maximum iterations for agentic workflows.
        enable_planning (bool): Flag to enable planning in agents.
        log_level (str): The logging level for the application.
        log_file (str): The file path for logging output.
        config_yaml_path (str): The path to the YAML configuration file.
    """

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
        """
        Validates the provided model name against a list of known models.

        Args:
            v (str): The model name to validate.

        Returns:
            str: The validated model name.

        Raises:
            ValueError: If the model name is not in the list of valid models.
        """
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
        """
        Validates the provided log level against a list of valid levels.

        Args:
            v (str): The log level to validate.

        Returns:
            str: The validated log level in uppercase.

        Raises:
            ValueError: If the log level is not in the list of valid levels.
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    def load_yaml_config(self) -> Dict[str, Any]:
        """
        Loads additional configuration from a YAML file.

        The path to the YAML file is specified by the `config_yaml_path`
        attribute. If the file does not exist, an empty dictionary is returned.

        Returns:
            Dict[str, Any]: A dictionary containing the YAML configuration, or
            an empty dictionary if the file doesn't exist.
        """
        yaml_path = Path(self.config_yaml_path)
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_model_for_task(self, task_type: str = "general") -> str:
        """
        Retrieves the optimal model name for a given task type from the YAML config.

        This allows for specialized models to be used for different tasks (e.g.,
        'reasoning', 'coding'). If a model for the specified task type is not
        found, the default model name is returned.

        Args:
            task_type (str, optional): The type of task. Defaults to "general".

        Returns:
            str: The recommended model name for the task.
        """
        yaml_config = self.load_yaml_config()
        models = yaml_config.get("models", {})

        # Map task type to model
        return models.get(task_type, self.model_name)

    def get_enabled_tools(self) -> List[str]:
        """
        Gets the list of enabled tool names from the YAML configuration.

        If the `enable_tools` setting is `False`, this returns an empty list.
        Otherwise, it reads the list of enabled tools from the 'tools' section
        of the YAML config.

        Returns:
            List[str]: A list of names of the enabled tools.
        """
        if not self.enable_tools:
            return []

        yaml_config = self.load_yaml_config()
        tools_config = yaml_config.get("tools", {})
        return tools_config.get("enabled", [])

    def get_agent_config(self) -> Dict[str, Any]:
        """
        Retrieves the agent configuration from the YAML file.

        This method fetches the 'agent' section from the YAML configuration,
        providing default values for key agent parameters if they are not
        specified.

        Returns:
            Dict[str, Any]: A dictionary containing the agent configuration.
        """
        yaml_config = self.load_yaml_config()
        agent_config = yaml_config.get("agent", {})

        return {
            "max_iterations": agent_config.get("max_iterations", self.max_agent_iterations),
            "enable_planning": agent_config.get("enable_planning", self.enable_planning),
            "enable_reasoning": agent_config.get("enable_reasoning", True),
            "timeout_seconds": agent_config.get("timeout_seconds", 300),
            "default_agent": agent_config.get("default_agent", "task_executor"),
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Retrieves a cached instance of the Settings object.

    This function uses an LRU (Least Recently Used) cache to ensure that the
    Settings object is instantiated only once, providing a singleton-like
    behavior for accessing application settings.

    Returns:
        Settings: The cached instance of the application settings.
    """
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
    """
    Calculates the estimated cost of an OpenAI API call based on token usage.

    This function uses a predefined pricing model for various GPT models to
    calculate the cost. If the specified model is not found in the pricing
    map, it defaults to 'gpt-4o' pricing.

    Args:
        model (str): The name of the model used for the API call.
        input_tokens (int): The number of tokens in the input prompt.
        output_tokens (int): The number of tokens in the generated response.

    Returns:
        float: The total calculated cost for the API call.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
