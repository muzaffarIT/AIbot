from backend.integrations.ai.kie_client import KieAPIError, KieClient
from backend.core.config import settings
from backend.integrations.ai.base import BaseAIProvider
from shared.dto.ai_payloads import GenerationResult
from shared.enums.providers import AIProvider


class NanoBananaProvider(BaseAIProvider):
    provider_name = AIProvider.NANO_BANANA
    output_extension = "png"
    api_key = settings.nano_banana_api_key or settings.kie_api_key

    def _real_generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
        job_payload: dict | None = None,
    ) -> GenerationResult:
        client = KieClient(api_key=self.api_key)
        input_payload = {
            "prompt": prompt,
            "output_format": "png",
            "image_size": "1:1",
        }
        if job_payload:
            input_payload.update(job_payload)
        if source_image_url:
            input_payload["image_urls"] = [source_image_url]

        model = "google/nano-banana-edit" if source_image_url else "google/nano-banana"
        task_id = client.create_market_task(
            model=model,
            input_payload=input_payload,
            callback_url=self._build_callback_url("nano-banana"),
        )
        task_info = client.wait_for_market_task(task_id)
        if not task_info.is_success or not task_info.result_url:
            raise KieAPIError(task_info.error_message or "Nano Banana task failed")

        return GenerationResult(
            external_job_id=task_info.task_id,
            result_url=task_info.result_url,
            result_payload=task_info.raw_result or "{}",
        )
