import time
import json
from ChatSystem.tools.tool_result import ToolExecutionResult, ToolStatus

def benchmark_tool_result():
    payload = {"results": [{"id": i, "data": "some data " * 10} for i in range(50)]}
    result = ToolExecutionResult(
        status=ToolStatus.SUCCESS,
        structured_payload=payload,
        duration=0.1,
        tool_name="test_tool"
    )

    iterations = 1000
    print(f"Benchmarking ToolExecutionResult.get_output ({iterations} iterations)...")

    start = time.perf_counter()
    for _ in range(iterations):
        result.get_output()
    duration = time.perf_counter() - start
    print(f"  Current duration: {duration:.4f}s ({duration/iterations*1000:.6f} ms/call)")

    # Test with separators and no indent
    def optimized_get_output(res):
        if res.structured_payload:
            return json.dumps(res.structured_payload, separators=(',', ':'))
        return res.stdout or res.stderr or ""

    start = time.perf_counter()
    for _ in range(iterations):
        optimized_get_output(result)
    duration_opt = time.perf_counter() - start
    print(f"  Optimized duration: {duration_opt:.4f}s ({duration_opt/iterations*1000:.6f} ms/call)")
    print(f"  Improvement: {(duration - duration_opt) / duration * 100:.2f}%")

    current_out = result.get_output()
    opt_out = optimized_get_output(result)
    print(f"\n  Current size: {len(current_out)} chars")
    print(f"  Optimized size: {len(opt_out)} chars")
    print(f"  Token saving (approx): {(len(current_out) - len(opt_out)) / 4:.1f} tokens")

if __name__ == "__main__":
    benchmark_tool_result()
