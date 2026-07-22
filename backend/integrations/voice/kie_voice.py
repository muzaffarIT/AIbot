"""KIE.ai voice client — speech-to-text and text-to-speech via ElevenLabs.

Both use the async job flow:  POST /api/v1/jobs/createTask  →  poll
GET /api/v1/jobs/recordInfo?taskId=…  until state is success/fail.

Parsing is defensive because KIE wraps ElevenLabs results in a `resultJson`
string whose exact shape varies (a transcript string for STT, a `resultUrls`
audio link for TTS).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class VoiceError(RuntimeError):
    """User-safe voice failure (provider down, bad audio, timeout)."""


class KieVoiceClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        poll_interval: float = 4.0,
        poll_timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key or settings.kie_api_key
        self.base_url = (base_url or settings.kie_base_url or "https://api.kie.ai").rstrip("/")
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    # ── public API ────────────────────────────────────────────────────────

    def transcribe(self, audio_url: str, *, language_code: str | None = None) -> str:
        """Speech → text. Returns the transcript (may be empty)."""
        input_block: dict[str, Any] = {"audio_url": audio_url}
        if language_code:
            input_block["language_code"] = language_code
        data = self._create_and_wait(settings.kie_stt_model, input_block)
        return _extract_transcript(data)

    def synthesize(self, text: str, *, voice: str | None = None) -> str:
        """Text → speech. Returns a URL to the generated audio."""
        input_block = {"text": text[:5000], "voice": voice or settings.kie_tts_voice}
        data = self._create_and_wait(settings.kie_tts_model, input_block)
        url = _extract_audio_url(data)
        if not url:
            raise VoiceError("Не удалось получить аудио.")
        return url

    # ── internals ─────────────────────────────────────────────────────────

    def _create_and_wait(self, model: str, input_block: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise VoiceError("Голос недоступен (нет ключа).")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        create_url = f"{self.base_url}/api/v1/jobs/createTask"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(create_url, headers=headers, json={"model": model, "input": input_block})
                resp.raise_for_status()
                created = resp.json()
        except httpx.HTTPError as exc:
            raise VoiceError("Голосовой сервис недоступен. Попробуйте позже.") from exc

        if created.get("code") not in (200, 0):
            raise VoiceError(_friendly(created.get("msg")))
        task_id = (created.get("data") or {}).get("taskId")
        if not task_id:
            raise VoiceError("Голосовой сервис не принял запрос.")

        # Poll recordInfo
        record_url = f"{self.base_url}/api/v1/jobs/recordInfo"
        elapsed = 0.0
        with httpx.Client(timeout=30.0) as client:
            while elapsed < self.poll_timeout:
                time.sleep(self.poll_interval)
                elapsed += self.poll_interval
                try:
                    r = client.get(record_url, headers=headers, params={"taskId": task_id})
                    d = (r.json() or {}).get("data") or {}
                except (httpx.HTTPError, ValueError):
                    continue
                state = d.get("state")
                if state == "success":
                    return d
                if state == "fail":
                    raise VoiceError(_friendly(d.get("failMsg")))
        raise VoiceError("Голос обрабатывается слишком долго. Попробуйте ещё раз.")


# ── parsing helpers ──────────────────────────────────────────────────────────

def _result_obj(data: dict[str, Any]) -> Any:
    rj = data.get("resultJson")
    if isinstance(rj, str) and rj.strip():
        try:
            return json.loads(rj)
        except ValueError:
            return rj
    return rj


def _extract_transcript(data: dict[str, Any]) -> str:
    obj = _result_obj(data)
    if isinstance(obj, dict):
        for key in ("text", "transcript", "transcription", "result"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        # some responses nest under "data" / "results"
        nested = obj.get("data") or obj.get("results")
        if isinstance(nested, dict):
            for key in ("text", "transcript", "transcription"):
                val = nested.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    if isinstance(obj, str) and obj.strip():
        return obj.strip()
    return ""


def _extract_audio_url(data: dict[str, Any]) -> str:
    obj = _result_obj(data)
    if isinstance(obj, dict):
        urls = obj.get("resultUrls")
        if isinstance(urls, list) and urls:
            return str(urls[0])
        for key in ("audio_url", "url", "audioUrl"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def _friendly(msg: str | None) -> str:
    raw = (msg or "").strip()
    low = raw.lower()
    if "internal error" in low or "try again" in low:
        return "Голос временно недоступен. Попробуйте позже."
    if "not found" in low or "not supported" in low:
        return "Голосовая модель недоступна."
    return raw or "Голосовой сервис вернул ошибку."
