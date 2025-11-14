#!/usr/bin/env python3
"""
ToolExecutionResult - Standardized tool execution result model

This module defines the contract for all tool executions in the ChatSystem.
Every tool execution must return a ToolExecutionResult to ensure:
1. Consistent error handling
2. Observable performance metrics
3. Structured telemetry data
4. Type-safe result handling
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class ToolStatus(str, Enum):
    """Tool execution status codes"""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    MANUAL_REQUIRED = "manual_required"


class ToolExecutionResult(BaseModel):
    """
    Standardized tool execution result.

    This model provides a contract for all tool executions, ensuring:
    - Structured status reporting (success/timeout/error/manual_required)
    - Separated stdout/stderr streams
    - Optional structured JSON payload
    - Performance metrics (duration, timestamp)
    - Tool metadata for telemetry
    - Debugging information (exit codes, commands)

    Attributes:
        status: Execution status (SUCCESS, TIMEOUT, ERROR, MANUAL_REQUIRED)
        stdout: Standard output from the tool
        stderr: Standard error output from the tool
        structured_payload: Parsed JSON data from stdout (if applicable)
        duration: Execution time in seconds
        timestamp: When the execution occurred
        tool_name: Name of the tool that was executed
        tool_version: Version of the tool (for tracking)
        has_side_effects: Whether the tool modifies files/state
        exit_code: Process exit code (if applicable)
        command: Full command executed (for debugging)
        error_message: Human-readable error message
        error_type: Exception/error type name
    """

    # Execution status
    status: ToolStatus

    # Output streams
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    # Structured data (parsed from stdout if JSON)
    structured_payload: Optional[Dict[str, Any]] = None

    # Performance metrics
    duration: float  # seconds
    timestamp: datetime = Field(default_factory=datetime.now)

    # Tool metadata
    tool_name: str
    tool_version: str = "1.0"
    has_side_effects: bool = False

    # Process details
    exit_code: Optional[int] = None
    command: Optional[str] = None  # For debugging

    # Error details
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    # Pydantic v2 configuration
    model_config = ConfigDict()

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamp to ISO format for JSON"""
        return value.isoformat()

    def is_success(self) -> bool:
        """Check if the execution was successful"""
        return self.status == ToolStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if the execution resulted in an error"""
        return self.status == ToolStatus.ERROR

    def is_timeout(self) -> bool:
        """Check if the execution timed out"""
        return self.status == ToolStatus.TIMEOUT

    def requires_manual_action(self) -> bool:
        """Check if manual action is required"""
        return self.status == ToolStatus.MANUAL_REQUIRED

    def get_output(self) -> str:
        """
        Get the primary output (structured_payload as JSON, or stdout)

        Returns:
            str: Primary output from the tool execution
        """
        if self.structured_payload:
            import json
            return json.dumps(self.structured_payload, indent=2)
        return self.stdout or self.stderr or ""

    def get_summary(self) -> str:
        """
        Get a one-line summary of the execution

        Returns:
            str: Summary like "analyze_python_code: SUCCESS (0.523s)"
        """
        return f"{self.tool_name}: {self.status.value.upper()} ({self.duration:.3f}s)"

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to legacy dict format for backward compatibility.

        Returns:
            Dict containing 'success' and 'result' or 'error' keys
        """
        if self.is_success():
            return {
                "success": True,
                "result": self.get_output()
            }
        else:
            # For manual_required status, preserve the message from stdout/structured_payload
            # For errors/timeouts, use error_message
            if self.status == ToolStatus.MANUAL_REQUIRED:
                message = self.stdout or (
                    self.structured_payload.get("message", "Manual intervention required")
                    if self.structured_payload else "Manual intervention required"
                )
                return {
                    "success": False,
                    "error": message,
                    "status": self.status.value,
                    "requires_manual_action": True
                }
            else:
                return {
                    "success": False,
                    "error": self.error_message or self.stderr or "Unknown error"
                }
