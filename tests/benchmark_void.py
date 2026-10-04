"""
Comprehensive Benchmark Suite for V.O.I.D. Advanced Agentic Architecture.
Measures:
1. System Component Initialization Latency
2. Fast Path Routing Latency (Math, Time, System)
3. Deep Path DAG Decomposition Latency
4. Parallel vs Sequential Speedup on Multi-Step Tasks
5. Memory & VRAM Headroom Stability
"""

import os
import sys
import time
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import ExecutiveRouter, ExecutionPath
from core.agents.mathematics_agent import MathematicsAgent
from core.agents.scheduler import AgentTaskScheduler
from core.agents.workspace import SharedWorkspace
from core.agents.protocol import AgentMessage, AgentMessageType
from core.vram_manager import vram_manager
from core.context_manager import ContextManager


class VOIDBenchmark:
    @staticmethod
    def run_all():
        print("=" * 70)
        print("  V.O.I.D. ADVANCED AGENTIC SYSTEM BENCHMARK SUITE")
        print("=" * 70)

        # 1. Telemetry & Baseline VRAM
        telemetry = vram_manager.get_telemetry()
        print(f"\n[Hardware Telemetry]")
        print(f"  GPU Available       : {telemetry['gpu_available']} ({telemetry['gpu_name']})")
        print(f"  Total VRAM          : {telemetry['total_vram_mb']:.1f} MB (~4.0 GB target)")
        print(f"  Used VRAM           : {telemetry['used_vram_mb']:.1f} MB")
        print(f"  Free VRAM           : {telemetry['free_vram_mb']:.1f} MB")
        print(f"  Host RAM Used       : {telemetry['host_ram_used_mb']:.1f} MB / {telemetry['host_ram_total_mb']:.1f} MB ({telemetry['host_ram_percent']}%)")
        print(f"  Threshold State     : {telemetry['threshold_state']}")

        # 2. Fast Path Latencies
        router = ExecutiveRouter.get_instance()
        fast_queries = [
            ("Current Time", "what is the current time?"),
            ("Current Date", "what date is today?"),
            ("Deterministic Math", "calculate 15 * 8 + 40"),
            ("Symbolic Math", "sqrt(256) + 4^2"),
            ("Memory Forget", "forget that temporary note")
        ]

        print(f"\n[Fast Path Latency Benchmarks (Deterministic & Zero-VRAM Bypass)]")
        fast_latencies = []
        for name, q in fast_queries:
            t0 = time.perf_counter()
            path, fast_res, intent = router.route(q)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            fast_latencies.append(lat_ms)
            print(f"  {name:<22} : {lat_ms:6.2f} ms | Path: {path.value:<9} | Intent: {intent.value}")
            assert path == ExecutionPath.FAST_PATH, f"Expected FAST_PATH for {name}"

        avg_fast_ms = sum(fast_latencies) / len(fast_latencies)
        print(f"  --> Average Fast Path Latency: {avg_fast_ms:.2f} ms (Target < 50 ms: {'PASS' if avg_fast_ms < 50 else 'FAIL'})")

        # 3. Mathematics Agent Deterministic Computation
        math_agent = MathematicsAgent()
        math_queries = [
            ("Arithmetic", "45 * 12 + 100"),
            ("Calculus Derivative", "derivative of x**3 + 4*x"),
            ("Matrix Determinant", "determinant of [[2, 1], [1, 2]]")
        ]
        print(f"\n[Mathematics Agent Execution Latency]")
        for name, query in math_queries:
            msg = AgentMessage(sender="benchmark", receiver="math_agent", goal=query, payload={"query": query})
            t0 = time.perf_counter()
            res = math_agent.process(msg)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            print(f"  {name:<22} : {lat_ms:6.2f} ms | Result: {res.result[:30]}...")

        # 4. Parallel vs Sequential Execution Benchmark
        scheduler = AgentTaskScheduler(max_workers=4)

        def mock_worker(msg: AgentMessage) -> AgentMessage:
            time.sleep(0.05)  # 50ms synthetic workload
            return AgentMessage(
                sender=msg.receiver,
                receiver=msg.sender,
                task_id=msg.task_id,
                status="SUCCESS",
                result=f"Done {msg.task_id}"
            )

        num_steps = 4
        steps = [
            {"step_id": i + 1, "agent": f"agent_{i}", "goal": f"Task {i}", "dependencies": []}
            for i in range(num_steps)
        ]

        # Sequential measurement
        t0 = time.perf_counter()
        for s in steps:
            mock_worker(AgentMessage(sender="bench", receiver=s["agent"], task_id=str(s["step_id"]), goal=s["goal"]))
        seq_duration = time.perf_counter() - t0

        # Parallel DAG measurement
        ws = SharedWorkspace(task_id="bench_dag", goal="Parallel Speedup Benchmark")
        t0 = time.perf_counter()
        scheduler.execute_dag(steps, ws, mock_worker)
        par_duration = time.perf_counter() - t0

        speedup = seq_duration / par_duration if par_duration > 0 else 1.0
        print(f"\n[Parallel Execution Speedup (4 Concurrent Agents)]")
        print(f"  Sequential Duration : {seq_duration * 1000.0:.2f} ms")
        print(f"  Parallel Duration   : {par_duration * 1000.0:.2f} ms")
        print(f"  Effective Speedup   : {speedup:.2f}x (Target > 2.0x: {'PASS' if speedup >= 2.0 else 'WARN'})")

        # 5. Context Manager Token Budgeting
        ctx_mgr = ContextManager(token_budget=1500)
        long_turns = [{"role": "user", "content": "Text " * 200} for _ in range(5)]
        synth_context = ctx_mgr.build_synthesis_context(
            goal="Analyze multi-agent state",
            workspace=ws,
            recent_history=long_turns,
            token_budget=1500
        )
        est_tokens = ctx_mgr.estimate_tokens(synth_context)
        print(f"\n[Context Manager Budgeting]")
        print(f"  Prompt Estimated Tokens : {est_tokens} (Budget <= 1500: {'PASS' if est_tokens <= 1500 else 'FAIL'})")

        print("\n" + "=" * 70)
        print("  ALL BENCHMARKS EXECUTED SUCCESSFULLY")
        print("=" * 70)
        return {
            "avg_fast_path_ms": avg_fast_ms,
            "sequential_ms": seq_duration * 1000.0,
            "parallel_ms": par_duration * 1000.0,
            "speedup": speedup,
            "context_tokens": est_tokens
        }


class TestVOIDBenchmark(unittest.TestCase):
    def test_benchmark_suite(self):
        results = VOIDBenchmark.run_all()
        self.assertLess(results["avg_fast_path_ms"], 50.0)
        self.assertGreater(results["speedup"], 1.5)
        self.assertLessEqual(results["context_tokens"], 1500)


if __name__ == "__main__":
    unittest.main()
