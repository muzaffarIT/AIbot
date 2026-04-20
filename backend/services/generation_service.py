import logging
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.user import User
from backend.db.repositories.generation_jobs import GenerationJobRepository
from backend.integrations.ai.kling_motion import KlingMotionProvider
from backend.integrations.ai.nanobanana import NanoBananaProvider
from backend.integrations.ai.veo import VeoProvider
from backend.services.balance_service import BalanceService
from backend.services.user_service import UserService
from backend.services.settings_service import SettingsService
from backend.models.order import Order
from backend.models.generation_job import GenerationJob
from shared.enums.credit_transaction_type import CreditTransactionType
from shared.enums.job_status import JobStatus
from shared.enums.providers import AIProvider
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

logger = logging.getLogger(__name__)
GENERATION_CREDIT_COSTS = {
    AIProvider.NANO_BANANA: 5,
    AIProvider.KLING: 40,
    AIProvider.VEO: 30,
}


class GenerationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = GenerationJobRepository(db)
        self.user_service = UserService(db)
        self.balance_service = BalanceService(db)
        self.settings_service = SettingsService(db)

    def _get_provider_client(self, provider: str):
        if provider == AIProvider.NANO_BANANA:
            return NanoBananaProvider()
        if provider == AIProvider.KLING:
            return KlingMotionProvider()
        if provider == AIProvider.VEO:
            return VeoProvider()
        raise ValueError("Unsupported AI provider")

    def _get_credit_cost(self, provider: str) -> int:
        try:
            return GENERATION_CREDIT_COSTS[AIProvider(provider)]
        except (KeyError, ValueError) as exc:
            raise ValueError("Unsupported AI provider") from exc

    def create_job_for_user(
        self,
        *,
        telegram_user_id: int,
        provider: str,
        prompt: str,
        original_prompt: str | None = None,
        source_image_url: str | None = None,
        job_payload: dict | None = None,
        credits: int | None = None,
        process_now: bool | None = None,
    ):
        if not prompt.strip():
            raise ValueError("Prompt is required")

        user = self.user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise ValueError("User not found")

        # Daily generation limit removed — credits alone gate usage.
        is_admin = user.telegram_user_id in settings.admin_ids_list

        logger.info(
            f"[ADMIN CHECK] telegram_id={user.telegram_user_id} "
            f"admin_ids={settings.admin_ids_list} "
            f"is_admin={is_admin}"
        )

        cost = credits if credits is not None else self._get_credit_cost(provider)
        
        if not is_admin:
            current_balance = self.balance_service.get_balance_value(user.id)
            if current_balance < cost:
                raise ValueError("Not enough credits")

        job = self.repo.create_job(
            user_id=user.id,
            provider=provider,
            prompt=prompt.strip(),
            original_prompt=original_prompt.strip() if original_prompt else None,
            source_image_url=source_image_url,
            status=JobStatus.PENDING,
            credits_reserved=cost if not is_admin else 0,
            job_payload=job_payload or {}
        )
        
        if not is_admin:
            self.balance_service.subtract_credits(
                user_id=user.id,
                amount=cost,
                transaction_type=CreditTransactionType.RESERVE,
                reference_type="generation_job",
                reference_id=str(job.id),
                comment=f"Credits reserved for {provider} generation job",
            )
            try:
                from bot.services.sheets import log_generation
                log_generation(
                    user_full_name=user.first_name or "—",
                    username=user.username,
                    telegram_id=user.telegram_user_id,
                    provider=provider,
                    credits_used=cost,
                    job_id=job.id,
                )
            except Exception as _se:
                logger.warning(f"[SHEETS] generation log failed: {_se}")
        else:
            logger.info(f"[ADMIN] No credit deduction for {user.telegram_user_id}")


        should_process_now = settings.generation_process_now if process_now is None else process_now
        if should_process_now:
            return self.process_job(job.id)
        self.enqueue_job(job.id)
        return job

    def enqueue_job(self, job_id: int) -> None:
        from worker.tasks.generation_tasks import run_generation_job

        run_generation_job.delay(job_id)

    def process_job(self, job_id: int):
        job = self.repo.get_by_id(job_id)
        if not job:
            raise ValueError("Job not found")

        if job.status == JobStatus.COMPLETED:
            return job
        if job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
            return job

        provider = self._get_provider_client(job.provider)
        self.repo.update_job(job, status=JobStatus.PROCESSING)

        try:
            result = provider.generate(
                prompt=job.prompt,
                source_image_url=job.source_image_url,
                job_payload=job.job_payload,
            )
            updated_job = self.repo.update_job(
                job,
                status=JobStatus.COMPLETED,
                external_job_id=result.external_job_id,
                result_url=result.result_url,
                result_payload=result.result_payload,
                completed=True,
            )
            
            # Check achievements
            try:
                user = self.db.query(User).filter(User.id == job.user_id).first()
                if user:
                    from bot.services.achievements import check_and_award_achievements
                    check_and_award_achievements(
                        db=self.db,
                        user_id=job.user_id,
                        telegram_id=user.telegram_user_id,
                        lang=user.language_code or "ru"
                    )
                    self.db.commit() # Commit achievements
            except Exception as e:
                logger.error(f"Error checking achievements after job {job.id}: {e}")
            
            return updated_job
        except Exception as exc:
            self.balance_service.add_credits(
                user_id=job.user_id,
                amount=job.credits_reserved,
                transaction_type=CreditTransactionType.REFUND,
                reference_type="generation_job",
                reference_id=str(job.id),
                comment=f"Refund after failed generation job {job.id}",
            )
            return self.repo.update_job(
                job,
                status=JobStatus.FAILED,
                error_message=str(exc),
                completed=True,
            )

    def get_job(self, job_id: int):
        return self.repo.get_by_id(job_id)

    def get_user_jobs(self, telegram_user_id: int, limit: int = 20):
        user = self.user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise ValueError("User not found")
        return self.repo.get_by_user_id(user.id, limit=limit)

    def cleanup_stale_jobs(self, minutes: int = 30):
        """Finds jobs in PENDING for > 30 mins, fails them and refunds credits."""
        from datetime import datetime, timedelta, timezone
        threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        stale_jobs = self.repo.session.query(self.repo.model).filter(
            self.repo.model.status == JobStatus.PENDING,
            self.repo.model.created_at <= threshold
        ).all()
        
        from backend.models.credit_transaction import CreditTransaction
        results = []
        for job in stale_jobs:
            # Idempotency: skip refund if already issued for this job
            already_refunded = self.db.query(CreditTransaction).filter(
                CreditTransaction.reference_type == "generation_job",
                CreditTransaction.reference_id == str(job.id),
                CreditTransaction.transaction_type == CreditTransactionType.REFUND,
            ).first()
            if not already_refunded:
                self.balance_service.add_credits(
                    user_id=job.user_id,
                    amount=job.credits_reserved,
                    transaction_type=CreditTransactionType.REFUND,
                    reference_type="generation_job",
                    reference_id=str(job.id),
                    comment=f"Timeout refund for job {job.id}",
                )
            self.repo.update_job(
                job,
                status=JobStatus.FAILED,
                error_message="Generation timeout (30 min)",
                completed=True
            )
            results.append(job)
        
        self.repo.session.commit()
        return results
