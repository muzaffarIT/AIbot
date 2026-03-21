from backend.integrations.ai.kie_client import KieAPIError, KieClient
from backend.core.config import settings
from backend.integrations.ai.base import BaseAIProvider
from shared.dto.ai_payloads import GenerationResult
from shared.enums.providers import AIProvider


class VeoProvider(BaseAIProvider):
    provider_name = AIProvider.VEO
    output_extension = "mp4"
    api_key = settings.veo_api_key or settings.kie_api_key

    def _real_generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
        job_payload: dict | None = None,
    ) -> GenerationResult:
        client = KieClient(api_key=self.api_key)
        payload = {
            "prompt": prompt,
            "model": "veo3_fast",
            "aspectRatio": "16:9",
            "callBackUrl": self._build_callback_url("veo"),
        }
        if job_payload:
            payload.update(job_payload)
        if source_image_url:
            payload["imageUrls"] = [source_image_url]

        task_id = client.create_veo_task(payload=payload)
        task_info = client.wait_for_veo_task(task_id)
        if not task_info.is_success or not task_info.result_url:
            raise KieAPIError(task_info.error_message or "Veo task failed")

        return GenerationResult(
            external_job_id=task_info.task_id,
            result_url=task_info.result_url,
            result_payload=task_info.raw_result or "{}",
        )
