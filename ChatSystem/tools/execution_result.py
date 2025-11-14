"""Data structures for normalized tool execution results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

TOOL_STATUS_SUCCESS = "success"
TOOL_STATUS_ERROR = "error"
TOOL_STATUS_TIMEOUT = "timeout"
TOOL_STATUS_MANUAL_REQUIRED = "manual_required"

StructuredPayload = Optional[Union[Dict[str, Any], Any]]


@dataclass
class ToolExecutionResult:
    """Normalized result returned from executing a tool."""

    status: str
    stdout: str = ""
    stderr: str = ""
    structured_payload: StructuredPayload = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the execution result into a JSON-friendly dictionary."""

        return {
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "structured_payload": self.structured_payload,
            "duration": self.duration,
            "metadata": self.metadata,
        }

    def to_legacy_response(self) -> Dict[str, Any]:
        """Convert the normalized structure back to the legacy dictionary format."""

        if self.status == TOOL_STATUS_SUCCESS:
            payload = (
                self.structured_payload
                if self.structured_payload is not None
                else self.stdout
            )
            return {"success": True, "result": payload}

        error_message = self.stderr or self.stdout or "Unknown tool execution error"
        if self.status == TOOL_STATUS_TIMEOUT:
            error_message = error_message or "Tool execution timed out"
        elif self.status == TOOL_STATUS_MANUAL_REQUIRED and not error_message:
            error_message = "Manual intervention required"

        return {
            "success": False,
            "error": error_message,
            "status": self.status,
            "result": self.structured_payload,
        }

    @classmethod
    def from_error(
        cls,
        message: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = TOOL_STATUS_ERROR,
    ) -> "ToolExecutionResult":
        """Helper to quickly create an error result."""

        return cls(
            status=status,
            stdout="",
            stderr=message,
            structured_payload={"error": message},
            duration=0.0,
            metadata=metadata or {},
        )
