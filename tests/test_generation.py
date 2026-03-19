import unittest

from tests.test_support import create_client
from backend.core.config import settings
from worker.celery_app import celery_app


class GenerationFlowTests(unittest.TestCase):
    def test_generation_job_completes_in_mock_mode_and_spends_credits(self) -> None:
        telegram_user_id = 303003

        with create_client() as client:
            client.post(
                "/api/users/ensure",
                json={
                    "telegram_user_id": telegram_user_id,
                    "username": "generator",
                    "first_name": "Mock",
                    "language_code": "ru",
                },
            )
            plan = client.get("/api/plans/").json()[0]
            order = client.post(
                "/api/orders/",
                json={
                    "telegram_user_id": telegram_user_id,
                    "plan_code": plan["code"],
                    "payment_method": "card",
                },
            ).json()
            payment = client.post(
                "/api/payments/",
                json={
                    "order_id": order["id"],
                    "provider": "cards",
                    "method": "card",
                },
            ).json()
            client.post(f"/api/payments/{payment['id']}/confirm")

            job_response = client.post(
                "/api/jobs/",
                json={
                    "telegram_user_id": telegram_user_id,
                    "provider": "nano_banana",
                    "prompt": "astronaut cat in cinematic lighting",
                },
            )
            self.assertEqual(job_response.status_code, 200)
            job = job_response.json()
            self.assertEqual(job["status"], "completed")
            self.assertTrue(job["result_url"].startswith("https://mock.local/nano_banana/"))
            self.assertEqual(job["credits_reserved"], 12)

            balance_response = client.get(f"/api/balances/telegram/{telegram_user_id}")
            self.assertEqual(balance_response.status_code, 200)
            self.assertEqual(
                balance_response.json()["credits_balance"],
                plan["credits_amount"] - 12,
            )

            jobs_response = client.get(f"/api/jobs/telegram/{telegram_user_id}")
            self.assertEqual(jobs_response.status_code, 200)
            self.assertEqual(len(jobs_response.json()["jobs"]), 1)

    def test_generation_job_rejects_when_balance_is_too_low(self) -> None:
        telegram_user_id = 303004

        with create_client() as client:
            client.post(
                "/api/users/ensure",
                json={
                    "telegram_user_id": telegram_user_id,
                    "username": "empty_wallet",
                    "first_name": "NoMoney",
                    "language_code": "ru",
                },
            )

            response = client.post(
                "/api/jobs/",
                json={
                    "telegram_user_id": telegram_user_id,
                    "provider": "veo",
                    "prompt": "aerial city flythrough at sunset",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Not enough credits")

    def test_generation_job_can_be_queued_and_processed_by_eager_celery(self) -> None:
        telegram_user_id = 303005
        original_process_now = settings.generation_process_now
        original_eager = celery_app.conf.task_always_eager

        settings.generation_process_now = False
        celery_app.conf.task_always_eager = True

        try:
            with create_client() as client:
                client.post(
                    "/api/users/ensure",
                    json={
                        "telegram_user_id": telegram_user_id,
                        "username": "queued_user",
                        "first_name": "Queued",
                        "language_code": "ru",
                    },
                )
                plan = client.get("/api/plans/").json()[0]
                order = client.post(
                    "/api/orders/",
                    json={
                        "telegram_user_id": telegram_user_id,
                        "plan_code": plan["code"],
                        "payment_method": "card",
                    },
                ).json()
                payment = client.post(
                    "/api/payments/",
                    json={
                        "order_id": order["id"],
                        "provider": "cards",
                        "method": "card",
                    },
                ).json()
                client.post(f"/api/payments/{payment['id']}/confirm")

                job_response = client.post(
                    "/api/jobs/",
                    json={
                        "telegram_user_id": telegram_user_id,
                        "provider": "kling",
                        "prompt": "smooth cinematic motion through a neon alley",
                    },
                )

                self.assertEqual(job_response.status_code, 200)
                job = job_response.json()
                self.assertEqual(job["status"], "pending")

                refreshed_job_response = client.get(f"/api/jobs/{job['id']}")
                self.assertEqual(refreshed_job_response.status_code, 200)
                refreshed_job = refreshed_job_response.json()
                self.assertEqual(refreshed_job["status"], "completed")
                self.assertTrue(
                    refreshed_job["result_url"].startswith("https://mock.local/kling/")
                )
        finally:
            settings.generation_process_now = original_process_now
            celery_app.conf.task_always_eager = original_eager
