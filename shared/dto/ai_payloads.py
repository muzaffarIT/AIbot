from dataclasses import dataclass


@dataclass(slots=True)
class GenerationResult:
    external_job_id: str
    result_url: str
    result_payload: str
