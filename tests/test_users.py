import unittest

from tests.test_support import create_client


class UserPaymentFlowTests(unittest.TestCase):
    def test_user_can_be_created_and_receive_credits_after_payment(self) -> None:
        telegram_user_id = 101001

        with create_client() as client:
            ensure_response = client.post(
                "/api/users/ensure",
                json={
                    "telegram_user_id": telegram_user_id,
                    "username": "maker",
                    "first_name": "Test",
                    "last_name": "User",
                    "language_code": "ru",
                },
            )
            self.assertEqual(ensure_response.status_code, 200)
            ensured_user = ensure_response.json()
            self.assertEqual(ensured_user["telegram_user_id"], telegram_user_id)
            self.assertEqual(ensured_user["credits_balance"], 0)

            plans_response = client.get("/api/plans/")
            self.assertEqual(plans_response.status_code, 200)
            plans = plans_response.json()
            self.assertGreaterEqual(len(plans), 1)
            selected_plan = plans[0]

            order_response = client.post(
                "/api/orders/",
                json={
                    "telegram_user_id": telegram_user_id,
                    "plan_code": selected_plan["code"],
                    "payment_method": "card",
                },
            )
            self.assertEqual(order_response.status_code, 200)
            order = order_response.json()
            self.assertEqual(order["status"], "pending")

            payment_response = client.post(
                "/api/payments/",
                json={
                    "order_id": order["id"],
                    "provider": "cards",
                    "method": "card",
                },
            )
            self.assertEqual(payment_response.status_code, 200)
            payment = payment_response.json()
            self.assertEqual(payment["status"], "created")

            waiting_orders_response = client.get(
                f"/api/orders/telegram/{telegram_user_id}?limit=5"
            )
            self.assertEqual(waiting_orders_response.status_code, 200)
            waiting_orders = waiting_orders_response.json()["orders"]
            self.assertEqual(waiting_orders[0]["status"], "waiting_payment")

            confirm_response = client.post(f"/api/payments/{payment['id']}/confirm")
            self.assertEqual(confirm_response.status_code, 200)
            confirmed_payment = confirm_response.json()
            self.assertEqual(confirmed_payment["status"], "paid")
            self.assertEqual(
                confirmed_payment["credited_amount"],
                selected_plan["credits_amount"],
            )
            self.assertEqual(
                confirmed_payment["current_balance"],
                selected_plan["credits_amount"],
            )

            balance_response = client.get(f"/api/balances/telegram/{telegram_user_id}")
            self.assertEqual(balance_response.status_code, 200)
            self.assertEqual(
                balance_response.json()["credits_balance"],
                selected_plan["credits_amount"],
            )

            history_response = client.get(
                f"/api/balances/telegram/{telegram_user_id}/transactions?limit=5"
            )
            self.assertEqual(history_response.status_code, 200)
            history = history_response.json()
            self.assertEqual(history["credits_balance"], selected_plan["credits_amount"])
            self.assertEqual(len(history["transactions"]), 1)
            self.assertEqual(
                history["transactions"][0]["amount"],
                selected_plan["credits_amount"],
            )

            final_orders_response = client.get(
                f"/api/orders/telegram/{telegram_user_id}?limit=5"
            )
            self.assertEqual(final_orders_response.status_code, 200)
            self.assertEqual(final_orders_response.json()["orders"][0]["status"], "paid")
