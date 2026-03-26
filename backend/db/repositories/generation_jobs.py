from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.generation_job import GenerationJob


class GenerationJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(
        self,
        *,
        user_id: int,
        provider: str,
        prompt: str,
        source_image_url: str | None,
        status: str,
        credits_reserved: int,
        job_payload: dict | None = None,
        original_prompt: str | None = None,
    ) -> GenerationJob:
        job = GenerationJob(
            user_id=user_id,
            provider=provider,
            prompt=prompt,
            source_image_url=source_image_url,
            status=status,
            credits_reserved=credits_reserved,
            job_payload=job_payload,
            original_prompt=original_prompt,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: int) -> GenerationJob | None:
        stmt = select(GenerationJob).where(GenerationJob.id == job_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: int, limit: int = 20) -> list[GenerationJob]:
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.user_id == user_id)
            .order_by(GenerationJob.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def update_job(
        self,
        job: GenerationJob,
        *,
        status: str | None = None,
        external_job_id: str | None = None,
        result_url: str | None = None,
        result_payload: str | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> GenerationJob:
        if status is not None:
            job.status = status
        if external_job_id is not None:
            job.external_job_id = external_job_id
        if result_url is not None:
            job.result_url = result_url
        if result_payload is not None:
            job.result_payload = result_payload
        if error_message is not None:
            job.error_message = error_message
        if completed:
            job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job
