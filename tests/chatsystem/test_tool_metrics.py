#!/usr/bin/env python3
"""
Unit tests for ToolMetrics telemetry.

Hermetic unit tests: metrics are exercised with pre-built ToolExecutionResult
objects, so no subprocess or live API is involved.
"""

import pytest

from ChatSystem.core.tool_metrics import ToolMetrics
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus


def _result(status, duration=0.1, error_message=None):
    """Build a ToolExecutionResult for a given status."""
    return ToolExecutionResult(
        status=status,
        duration=duration,
        tool_name="test_tool",
        error_message=error_message,
    )


class TestToolMetrics:
    """Counters, rates, health, and error history."""

    def test_record_success_increments_count(self):
        m = ToolMetrics(tool_name="test_tool")
        m.record_execution(_result(ToolStatus.SUCCESS))
        assert m.success_count == 1
        assert m.total_calls == 1

    def test_record_error_tracks_last_error(self):
        m = ToolMetrics(tool_name="test_tool")
        m.record_execution(_result(ToolStatus.ERROR, error_message="boom"))
        assert m.error_count == 1
        assert m.last_error == "boom"

    def test_record_timeout(self):
        m = ToolMetrics(tool_name="test_tool")
        m.record_execution(_result(ToolStatus.TIMEOUT))
        assert m.timeout_count == 1
        assert m.last_error == "Timeout"

    def test_record_manual_required(self):
        m = ToolMetrics(tool_name="test_tool")
        m.record_execution(_result(ToolStatus.MANUAL_REQUIRED))
        assert m.manual_required_count == 1

    def test_total_calls_sums_all_statuses(self):
        m = ToolMetrics(tool_name="t")
        m.record_execution(_result(ToolStatus.SUCCESS))
        m.record_execution(_result(ToolStatus.ERROR, error_message="e"))
        m.record_execution(_result(ToolStatus.TIMEOUT))
        m.record_execution(_result(ToolStatus.MANUAL_REQUIRED))
        assert m.total_calls == 4

    def test_success_rate(self):
        m = ToolMetrics(tool_name="t")
        for _ in range(3):
            m.record_execution(_result(ToolStatus.SUCCESS))
        m.record_execution(_result(ToolStatus.ERROR, error_message="e"))
        assert m.success_rate == 75.0

    def test_rates_zero_when_no_calls(self):
        m = ToolMetrics(tool_name="t")
        assert m.success_rate == 0.0
        assert m.avg_duration == 0.0

    def test_avg_duration(self):
        m = ToolMetrics(tool_name="t")
        m.record_execution(_result(ToolStatus.SUCCESS, duration=0.5))
        m.record_execution(_result(ToolStatus.SUCCESS, duration=1.0))
        assert m.avg_duration == 0.75

    def test_health_status_healthy_at_90_percent(self):
        m = ToolMetrics(tool_name="t")
        for _ in range(9):
            m.record_execution(_result(ToolStatus.SUCCESS))
        m.record_execution(_result(ToolStatus.ERROR, error_message="e"))
        assert m.get_health_status() == "healthy"

    def test_health_status_degraded_at_80_percent(self):
        m = ToolMetrics(tool_name="t")
        for _ in range(8):
            m.record_execution(_result(ToolStatus.SUCCESS))
        for _ in range(2):
            m.record_execution(_result(ToolStatus.ERROR, error_message="e"))
        assert m.get_health_status() == "degraded"

    def test_health_status_unhealthy_at_50_percent(self):
        m = ToolMetrics(tool_name="t")
        for _ in range(5):
            m.record_execution(_result(ToolStatus.SUCCESS))
        for _ in range(5):
            m.record_execution(_result(ToolStatus.ERROR, error_message="e"))
        assert m.get_health_status() == "unhealthy"

    def test_health_status_unknown_with_no_calls(self):
        assert ToolMetrics(tool_name="t").get_health_status() == "unknown"

    def test_error_history_capped_at_10(self):
        m = ToolMetrics(tool_name="t")
        for i in range(12):
            m.record_execution(_result(ToolStatus.ERROR, error_message=f"err{i}"))
        assert len(m.error_history) == 10
        # deque keeps the most recent 10 (err2..err11); err0/err1 are dropped
        assert any(entry.endswith(": err11") for entry in m.error_history)
        assert not any(entry.endswith(": err0") for entry in m.error_history)

    def test_to_dict_is_cached_and_copy_safe(self):
        m = ToolMetrics(tool_name="t")
        m.record_execution(_result(ToolStatus.SUCCESS))
        first = m.to_dict()
        assert m.to_dict() == first
        # Mutating the returned dict must not corrupt internal cache
        first["tool_name"] = "mutated"
        assert m.to_dict()["tool_name"] == "t"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
