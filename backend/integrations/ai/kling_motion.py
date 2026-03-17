from backend.integrations.ai.kie_client import KieAPIError, KieClient
from backend.core.config import settings
from backend.integrations.ai.base import BaseAIProvider
from shared.dto.ai_payloads import GenerationResult
from shared.enums.providers import AIProvider


class KlingMotionProvider(BaseAIProvider):
    provider_name = AIProvider.KLING
    output_extension = "mp4"
    api_key = settings.kling_api_key or settings.kie_api_key

    def _real_generate(
        self,
        *,
        prompt: str,
        source_image_url: str | None = None,
    ) -> GenerationResult:
        client = KieClient(api_key=self.api_key)
        input_payload = {
            "prompt": prompt,
            "sound": False,
            "duration": "5",
        }
        model = "kling-3.0/video"
        if source_image_url:
            input_payload["image_urls"] = [source_image_url]
            input_payload["multi_shots"] = False
            input_payload["mode"] = "std"
            input_payload["aspect_ratio"] = "16:9"

        task_id = client.create_market_task(
            model=model,
            input_payload=input_payload,
            callback_url=self._build_callback_url("kling"),
        )
        task_info = client.wait_for_market_task(task_id)
        if not task_info.is_success or not task_info.result_url:
            raise KieAPIError(task_info.error_message or "Kling task failed")

        return GenerationResult(
            external_job_id=task_info.task_id,
            result_url=task_info.result_url,
            result_payload=task_info.raw_result or "{}",
        )
