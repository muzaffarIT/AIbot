import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from backend.core.config import settings


class KieAPIError(RuntimeError):
    pass


@dataclass(slots=True)
class KieTaskInfo:
    task_id: str
    state: str
    result_url: str | None
    raw_result: str | None
    error_message: str | None

    @property
    def is_success(self) -> bool:
        return self.state in {"success", "completed"}

    @property
    def is_failure(self) -> bool:
        return self.state in {"fail", "failed", "error"}

    @property
    def is_terminal(self) -> bool:
        return self.is_success or self.is_failure


class KieClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key or settings.kie_api_key
        self.base_url = (base_url or settings.kie_base_url or "https://api.kie.ai").rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise KieAPIError("KIE_API_KEY is not configured")

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.base_url, path.lstrip("/"))

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json_payload,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise KieAPIError(f"Invalid JSON response from Kie API: {response.text}") from exc

        if response.status_code >= 400:
            raise KieAPIError(payload.get("msg") or f"Kie API request failed: {response.status_code}")

        if payload.get("code") not in (None, 200):
            raise KieAPIError(payload.get("msg") or "Kie API returned an error")

        return payload

    def _extract_result_url(self, data: dict[str, Any]) -> tuple[str | None, str | None]:
        if "response" in data and isinstance(data["response"], dict):
            response_data = data["response"]
            result_urls = response_data.get("resultUrls") or response_data.get("originUrls") or []
            return (
                result_urls[0] if isinstance(result_urls, list) and result_urls else None,
                json.dumps(response_data, ensure_ascii=True, sort_keys=True),
            )

        result_json = data.get("resultJson")
        if isinstance(result_json, str) and result_json:
            try:
                parsed_result = json.loads(result_json)
            except json.JSONDecodeError:
                parsed_result = {"raw": result_json}

            result_urls = parsed_result.get("resultUrls") or parsed_result.get("originUrls") or []
            return (
                result_urls[0] if isinstance(result_urls, list) and result_urls else None,
                json.dumps(parsed_result, ensure_ascii=True, sort_keys=True),
            )

        return None, None

    def create_market_task(
        self,
        *,
        model: str,
        input_payload: dict[str, Any],
        callback_url: str | None = None,
    ) -> str:
        payload = {
            "model": model,
            "input": input_payload,
        }
        if callback_url:
            payload["callBackUrl"] = callback_url

        response = self._request("POST", "/api/v1/jobs/createTask", json_payload=payload)
        task_id = response.get("data", {}).get("taskId")
        if not task_id:
            raise KieAPIError("Kie market task response does not contain taskId")
        return str(task_id)

    def get_market_task(self, task_id: str) -> KieTaskInfo:
        response = self._request(
            "GET",
            "/api/v1/jobs/recordInfo",
            params={"taskId": task_id},
        )
        data = response.get("data", {})
        state = str(data.get("state", "unknown")).lower()
        result_url, raw_result = self._extract_result_url(data)
        return KieTaskInfo(
            task_id=str(data.get("taskId", task_id)),
            state=state,
            result_url=result_url,
            raw_result=raw_result,
            error_message=data.get("failMsg") or data.get("errorMessage"),
        )

    def create_veo_task(
        self,
        *,
        payload: dict[str, Any],
    ) -> str:
        response = self._request("POST", "/api/v1/veo/generate", json_payload=payload)
        task_id = response.get("data", {}).get("taskId")
        if not task_id:
            raise KieAPIError("Kie Veo response does not contain taskId")
        return str(task_id)

    def get_veo_task(self, task_id: str) -> KieTaskInfo:
        response = self._request(
            "GET",
            "/api/v1/veo/record-info",
            params={"taskId": task_id},
        )
        data = response.get("data", {})
        success_flag = data.get("successFlag")
        if success_flag == 1:
            state = "success"
        elif success_flag == 0:
            state = "generating"
        else:
            state = "fail" if data.get("errorMessage") else "unknown"

        result_url, raw_result = self._extract_result_url(data)
        return KieTaskInfo(
            task_id=str(data.get("taskId", task_id)),
            state=state,
            result_url=result_url,
            raw_result=raw_result,
            error_message=data.get("errorMessage"),
        )

    def wait_for_market_task(self, task_id: str) -> KieTaskInfo:
        return self._wait(task_id, self.get_market_task)

    def wait_for_veo_task(self, task_id: str) -> KieTaskInfo:
        return self._wait(task_id, self.get_veo_task)

    def _wait(self, task_id: str, getter) -> KieTaskInfo:
        last_info: KieTaskInfo | None = None

        for _ in range(settings.generation_poll_attempts):
            last_info = getter(task_id)
            if last_info.is_terminal:
                return last_info
            time.sleep(settings.generation_poll_interval_seconds)

        raise KieAPIError(
            f"Timed out waiting for Kie task {task_id}. Last state: {last_info.state if last_info else 'unknown'}"
        )
