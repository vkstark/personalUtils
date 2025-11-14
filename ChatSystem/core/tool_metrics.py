#!/usr/bin/env python3
"""
ToolMetrics - Per-tool telemetry tracking

This module provides comprehensive metrics tracking for each tool, enabling:
1. Success/failure rate monitoring
2. Performance analysis (latency, timeouts)
3. Error tracking and diagnostics
4. Health dashboards and alerting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

# Import at runtime to avoid circular dependency
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..tools.tool_result import ToolExecutionResult, ToolStatus


@dataclass
class ToolMetrics:
    """
    Comprehensive metrics for a single tool.

    Tracks:
    - Success/error/timeout/manual_required counts
    - Performance metrics (min/max/avg duration)
    - Recent error history (last 10 errors)
    - Timestamps of last success and error

    This enables:
    - Health dashboards (/health command)
    - Alerting on high failure rates
    - Performance regression detection
    - Debugging tool reliability issues
    """

    tool_name: str

    # Counters
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    manual_required_count: int = 0

    # Performance metrics (in seconds)
    total_duration: float = 0.0
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None

    # Timestamps
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    # Error history (last 10 errors)
    error_history: List[str] = field(default_factory=list)

    def record_execution(self, result: "ToolExecutionResult") -> None:
        """
        Update metrics from a tool execution result.

        Args:
            result: The ToolExecutionResult to record
        """
        from ..tools.tool_result import ToolStatus

        # Update counters based on status
        if result.status == ToolStatus.SUCCESS:
            self.success_count += 1
            self.last_success = result.timestamp

        elif result.status == ToolStatus.ERROR:
            self.error_count += 1
            self.last_error = result.error_message or "Unknown error"
            self.last_error_time = result.timestamp

            # Add to error history (keep last 10)
            error_entry = f"{result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {result.error_message or 'Unknown error'}"
            self.error_history.append(error_entry)
            if len(self.error_history) > 10:
                self.error_history = self.error_history[-10:]

        elif result.status == ToolStatus.TIMEOUT:
            self.timeout_count += 1
            self.last_error = "Timeout"
            self.last_error_time = result.timestamp

        elif result.status == ToolStatus.MANUAL_REQUIRED:
            self.manual_required_count += 1

        # Update performance metrics
        self.total_duration += result.duration

        if self.min_duration is None or result.duration < self.min_duration:
            self.min_duration = result.duration

        if self.max_duration is None or result.duration > self.max_duration:
            self.max_duration = result.duration

    @property
    def total_calls(self) -> int:
        """Total number of tool calls"""
        return (
            self.success_count +
            self.error_count +
            self.timeout_count +
            self.manual_required_count
        )

    @property
    def avg_duration(self) -> float:
        """Average execution duration in seconds"""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration / self.total_calls

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)"""
        if self.total_calls == 0:
            return 0.0
        return (self.success_count / self.total_calls) * 100

    @property
    def error_rate(self) -> float:
        """Error rate as a percentage (0-100)"""
        if self.total_calls == 0:
            return 0.0
        return (self.error_count / self.total_calls) * 100

    @property
    def timeout_rate(self) -> float:
        """Timeout rate as a percentage (0-100)"""
        if self.total_calls == 0:
            return 0.0
        return (self.timeout_count / self.total_calls) * 100

    def is_healthy(self, success_rate_threshold: float = 90.0) -> bool:
        """
        Check if the tool is healthy based on success rate.

        Args:
            success_rate_threshold: Minimum success rate to be considered healthy (default: 90%)

        Returns:
            bool: True if success rate >= threshold
        """
        if self.total_calls == 0:
            return True  # No data yet, assume healthy
        return self.success_rate >= success_rate_threshold

    def get_health_status(self) -> str:
        """
        Get human-readable health status.

        Returns:
            str: "healthy", "degraded", or "unhealthy"
        """
        if self.total_calls == 0:
            return "unknown"

        if self.success_rate >= 90:
            return "healthy"
        elif self.success_rate >= 70:
            return "degraded"
        else:
            return "unhealthy"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to a dictionary for serialization.

        Returns:
            Dict containing all metrics in a JSON-serializable format
        """
        return {
            "tool_name": self.tool_name,
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "timeout_count": self.timeout_count,
            "manual_required_count": self.manual_required_count,
            "success_rate": f"{self.success_rate:.1f}%",
            "error_rate": f"{self.error_rate:.1f}%",
            "timeout_rate": f"{self.timeout_rate:.1f}%",
            "avg_duration": f"{self.avg_duration:.3f}s",
            "min_duration": f"{self.min_duration:.3f}s" if self.min_duration is not None else "N/A",
            "max_duration": f"{self.max_duration:.3f}s" if self.max_duration is not None else "N/A",
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "health_status": self.get_health_status(),
        }

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"ToolMetrics(tool={self.tool_name}, "
            f"calls={self.total_calls}, "
            f"success_rate={self.success_rate:.1f}%, "
            f"avg_duration={self.avg_duration:.3f}s)"
        )
