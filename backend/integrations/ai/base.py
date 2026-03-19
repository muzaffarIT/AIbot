import json
from abc import ABC, abstractmethod
from uuid import uuid4

from backend.core.config import settings
from shared.dto.ai_payloads import GenerationResult


class BaseAIProvider(ABC):
    provider_name: str
    output_extension: str
    api_key: str | None = None

    def generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
    ) -> GenerationResult:
        if settings.ai_mock_mode or not self.api_key:
            return self._mock_generate(prompt=prompt, source_image_url=source_image_url)
        return self._real_generate(prompt=prompt, source_image_url=source_image_url)

    def _mock_generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
    ) -> GenerationResult:
        job_id = uuid4().hex
        source = source_image_url or ""
        return GenerationResult(
            external_job_id=f"mock-{self.provider_name}-{job_id}",
            result_url=f"https://mock.local/{self.provider_name}/{job_id}.{self.output_extension}",
            result_payload=json.dumps(
                {
                    "mode": "mock",
                    "provider": str(self.provider_name),
                    "prompt": prompt,
                    "source_image_url": source,
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
        )

    def _build_callback_url(self, route_suffix: str | None = None) -> str | None:
        base_url = settings.generation_callback_base_url
        if not base_url:
            return None

        route = "/api/ai/callback"
        if route_suffix:
            route = f"{route}/{route_suffix.strip('/')}"
        return f"{base_url.rstrip('/')}{route}"

    @abstractmethod
    def _real_generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
    ) -> GenerationResult:
        raise NotImplementedError
