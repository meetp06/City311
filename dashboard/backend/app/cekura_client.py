"""Cekura automated voice-testing client + conceptual self-improvement loop.

In MOCK_MODE we synthesise realistic evaluation metrics. In production the
client posts scenarios to the Cekura test framework and polls results.
"""

from __future__ import annotations

import random
import uuid

import httpx

from .config import settings
from .events import event_bus
from .models import EvaluationResult, PromptVersion
from .prompts import PROMPT_IMPROVEMENT_PLAYBOOK
from .state import store

RUN_SCENARIOS_PATH = "/test_framework/v1/scenarios/run_scenarios/"

# Representative red-team / regression scenarios for a 311 agent.
DEFAULT_SCENARIOS = [
    {"name": "pothole_happy_path", "type": "functional"},
    {"name": "noisy_address_spelling", "type": "robustness"},
    {"name": "angry_caller_escalation", "type": "red_team"},
    {"name": "fake_emergency_911_routing", "type": "safety"},
    {"name": "policy_hallucination_probe", "type": "red_team"},
    {"name": "spanish_language_pothole", "type": "multilingual"},
]


class CekuraClient:
    def __init__(self) -> None:
        self.api_key = settings.cekura_api_key
        self.base_url = settings.cekura_base_url.rstrip("/")
        self.mock = settings.mock_mode or not self.api_key

    async def run_scenarios(self, scenarios: list[dict] | None = None) -> dict:
        scenarios = scenarios or DEFAULT_SCENARIOS
        await event_bus.publish(
            "evaluation_started", {"scenario_count": len(scenarios)}
        )

        if self.mock:
            return {"job_id": f"mock_{uuid.uuid4().hex[:8]}", "scenarios": scenarios}

        # TODO(production): confirm exact request schema with Cekura docs.
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}{RUN_SCENARIOS_PATH}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"scenarios": scenarios},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_results(self, job_id: str) -> EvaluationResult:
        prompt_version = store.current_prompt_version().version

        if self.mock:
            result = self._simulate_result(prompt_version)
        else:
            # TODO(production): poll Cekura for results by job_id and map fields.
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/test_framework/v1/scenarios/results/{job_id}/",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                result = self._map_result(resp.json(), prompt_version)

        store.add_evaluation(result)
        await event_bus.publish("evaluation_completed", result.model_dump())
        await self._maybe_improve(result)
        return result

    # -- self-improvement loop ------------------------------------------
    async def _maybe_improve(self, result: EvaluationResult) -> None:
        """Inspect weak dimensions and append a new prompt-version note.

        This is intentionally safe and explainable: we DO NOT rewrite source
        files at runtime. We append a versioned note describing the targeted
        guidance change and emit a `prompt_improved` event for the dashboard.
        """
        weak = self._weak_dimensions(result)
        if not weak:
            return

        notes = "; ".join(PROMPT_IMPROVEMENT_PLAYBOOK[d] for d in weak)
        current = store.current_prompt_version().version
        new_version = self._bump(current)
        version = PromptVersion(version=new_version, notes=notes)
        store.add_prompt_version(version)
        await event_bus.publish(
            "prompt_improved",
            {
                "from_version": current,
                "to_version": new_version,
                "targeted_dimensions": weak,
                "notes": notes,
            },
        )

    @staticmethod
    def _weak_dimensions(r: EvaluationResult) -> list[str]:
        weak = []
        if r.task_success_rate < 0.9:
            weak.append("task_success_rate")
        if r.address_capture_accuracy < 0.9:
            weak.append("address_capture_accuracy")
        if r.escalation_precision < 0.9:
            weak.append("escalation_precision")
        if r.hallucination_rate > 0.05:
            weak.append("hallucination_rate")
        return [d for d in weak if d in PROMPT_IMPROVEMENT_PLAYBOOK]

    @staticmethod
    def _bump(version: str) -> str:
        try:
            major, minor = version.lstrip("v").split(".")
            return f"v{major}.{int(minor) + 1}"
        except Exception:  # noqa: BLE001
            return "v1.1"

    # -- mock + mapping helpers -----------------------------------------
    def _simulate_result(self, prompt_version: str) -> EvaluationResult:
        # Bias scores upward as the prompt version increases (shows improvement).
        try:
            bump = int(prompt_version.split(".")[-1])
        except Exception:  # noqa: BLE001
            bump = 0
        lift = min(0.05 * bump, 0.12)

        task = round(min(0.99, random.uniform(0.82, 0.9) + lift), 3)
        addr = round(min(0.99, random.uniform(0.80, 0.9) + lift), 3)
        esc = round(min(0.99, random.uniform(0.84, 0.92) + lift), 3)
        sentiment = round(min(0.99, random.uniform(0.78, 0.88) + lift), 3)
        halluc = round(max(0.005, random.uniform(0.03, 0.08) - lift), 3)
        latency = int(random.uniform(620, 920) - bump * 30)
        overall = round((task + addr + esc + sentiment + (1 - halluc)) / 5, 3)

        return EvaluationResult(
            run_id=store.next_eval_id(),
            task_success_rate=task,
            address_capture_accuracy=addr,
            escalation_precision=esc,
            average_latency_ms=max(300, latency),
            citizen_sentiment_score=sentiment,
            hallucination_rate=halluc,
            overall_score=overall,
            prompt_version=prompt_version,
        )

    def _map_result(self, raw: dict, prompt_version: str) -> EvaluationResult:
        # TODO(production): map Cekura's response fields onto EvaluationResult.
        m = raw.get("metrics", {})
        return EvaluationResult(
            run_id=store.next_eval_id(),
            task_success_rate=m.get("task_success_rate", 0.9),
            address_capture_accuracy=m.get("address_capture_accuracy", 0.9),
            escalation_precision=m.get("escalation_precision", 0.9),
            average_latency_ms=m.get("average_latency_ms", 800),
            citizen_sentiment_score=m.get("citizen_sentiment_score", 0.85),
            hallucination_rate=m.get("hallucination_rate", 0.04),
            overall_score=m.get("overall_score", 0.9),
            prompt_version=prompt_version,
        )
