"""NVIDIA NIM adapter for high-accuracy address transcription / verification.

Used as a secondary, high-accuracy pass for hard-to-transcribe addresses.
In MOCK_MODE it cleans and normalises text deterministically. In production
it should call a hosted NIM ASR / NeMo endpoint with NVIDIA_API_KEY.
"""

from __future__ import annotations

import re

import httpx

from ..config import settings


class NvidiaNimASRService:
    def __init__(self) -> None:
        self.api_key = settings.nvidia_api_key
        self.mock = settings.mock_mode

    async def transcribe_address(self, audio_or_text: str) -> dict:
        """Return a cleaned, verified address string with a confidence score."""
        if self.mock or not self.api_key:
            cleaned = self._normalise(audio_or_text)
            return {
                "address": cleaned,
                "confidence": 0.97,
                "source": "nvidia-nim-mock",
            }

        # TODO(production): call the NVIDIA NIM ASR / address-verification
        # endpoint. Example shape (endpoint + payload depend on the model):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://integrate.api.nvidia.com/v1/asr/transcribe",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"input": audio_or_text},
                )
                resp.raise_for_status()
                data = resp.json()
            return {
                "address": data.get("text", audio_or_text),
                "confidence": data.get("confidence", 0.9),
                "source": "nvidia-nim",
            }
        except Exception as exc:  # noqa: BLE001 — degrade gracefully for demo
            return {
                "address": self._normalise(audio_or_text),
                "confidence": 0.5,
                "source": f"nvidia-nim-error:{type(exc).__name__}",
            }

    @staticmethod
    def _normalise(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = text.title()
        # Fix ordinals after title-casing: "5Th" -> "5th".
        text = re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), text)
        return text
