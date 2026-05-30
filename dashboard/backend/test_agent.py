"""CLI to trigger a Cekura evaluation run and print a summary.

Runs against a live backend (default http://localhost:7860). Demonstrates the
before/after prompt-optimization concept by running two evals back to back so
the self-improvement loop bumps the prompt version between them.

Usage:
    cd backend
    python test_agent.py
    python test_agent.py --base-url http://localhost:7860 --runs 2
"""

from __future__ import annotations

import argparse
import json

import httpx


def _print_result(label: str, result: dict) -> None:
    print(f"\n=== {label} (run {result['run_id']}, prompt {result['prompt_version']}) ===")
    rows = [
        ("Task success rate", f"{result['task_success_rate'] * 100:.1f}%"),
        ("Address capture accuracy", f"{result['address_capture_accuracy'] * 100:.1f}%"),
        ("Escalation precision", f"{result['escalation_precision'] * 100:.1f}%"),
        ("Avg latency", f"{result['average_latency_ms']} ms"),
        ("Citizen sentiment", f"{result['citizen_sentiment_score'] * 100:.1f}%"),
        ("Hallucination rate", f"{result['hallucination_rate'] * 100:.2f}%"),
        ("Overall score", f"{result['overall_score'] * 100:.1f}%"),
    ]
    width = max(len(k) for k, _ in rows)
    for k, v in rows:
        print(f"  {k:<{width}} : {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 311 agent evaluations.")
    parser.add_argument("--base-url", default="http://localhost:7861")
    parser.add_argument("--runs", type=int, default=2)
    args = parser.parse_args()

    print(f"[test_agent] Running {args.runs} evaluation(s) against {args.base_url}")

    first = None
    last = None
    with httpx.Client(timeout=60.0, base_url=args.base_url) as client:
        for i in range(args.runs):
            resp = client.post("/api/evals/run")
            resp.raise_for_status()
            data = resp.json()
            result = data["result"]
            _print_result(f"Evaluation #{i + 1}", result)
            if first is None:
                first = result
            last = result

        history = client.get("/api/evals/history").json()

    if first and last and first is not last:
        delta = (last["overall_score"] - first["overall_score"]) * 100
        print("\n--- Self-improvement loop ---")
        print(f"  Prompt versions: {[v['version'] for v in history['prompt_versions']]}")
        for v in history["prompt_versions"][1:]:
            print(f"  {v['version']}: {v['notes']}")
        print(f"  Overall score change: {delta:+.1f} points")


if __name__ == "__main__":
    main()
