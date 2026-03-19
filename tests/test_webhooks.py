import unittest

from tests.test_support import create_client


class PaymentWebhookTests(unittest.TestCase):
    def test_cards_webhook_confirms_payment(self) -> None:
        telegram_user_id = 202002

        with create_client() as client:
            client.post(
                "/api/users/ensure",
                json={
                    "telegram_user_id": telegram_user_id,
                    "username": "cards_user",
                    "first_name": "Cards",
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

            webhook_response = client.post(
                "/api/webhooks/cards/",
                json={
                    "payment_id": payment["id"],
                    "provider_payment_id": payment["provider_payment_id"],
                    "transaction_id": "txn_cards_001",
                    "status": "paid",
                    "amount": plan["price"],
                    "currency": plan["currency"],
                },
                headers={"x-cards-secret": "cards-secret"},
            )

            self.assertEqual(webhook_response.status_code, 200)
            self.assertEqual(webhook_response.json()["payment_status"], "paid")

            payments_response = client.get(f"/api/payments/order/{order['id']}")
            self.assertEqual(payments_response.status_code, 200)
            order_payments = payments_response.json()["payments"]
            self.assertEqual(order_payments[0]["status"], "paid")
            self.assertEqual(order_payments[0]["provider_transaction_id"], "txn_cards_001")

            balance_response = client.get(f"/api/balances/telegram/{telegram_user_id}")
            self.assertEqual(balance_response.status_code, 200)
            self.assertEqual(balance_response.json()["credits_balance"], plan["credits_amount"])

    def test_cards_webhook_rejects_invalid_secret(self) -> None:
        with create_client() as client:
            response = client.post(
                "/api/webhooks/cards/",
                json={"payment_id": 1, "status": "paid"},
                headers={"x-cards-secret": "wrong-secret"},
            )

        self.assertEqual(response.status_code, 401)
