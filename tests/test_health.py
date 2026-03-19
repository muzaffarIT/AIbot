import unittest

from tests.test_support import create_client


class HealthApiTests(unittest.TestCase):
    def test_health_endpoint_returns_ok(self) -> None:
        with create_client() as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
