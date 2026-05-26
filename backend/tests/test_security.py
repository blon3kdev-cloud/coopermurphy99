"""Security hardening tests."""
from __future__ import annotations

import os
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_SECRET", "test-internal-secret-32chars")
os.environ.setdefault("NODE_ENV", "development")

from fastapi import HTTPException  # noqa: E402

from app.security import generate_otp  # noqa: E402
from app.wallet_service import hold_withdraw_balance  # noqa: E402


class OtpGenerationTests(unittest.TestCase):
    def test_generate_otp_is_six_digits(self):
        for _ in range(20):
            code = generate_otp()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())
            self.assertGreaterEqual(int(code), 100_000)
            self.assertLessEqual(int(code), 999_999)


class WalletHoldTests(unittest.IsolatedAsyncioTestCase):
    async def test_hold_raises_when_insufficient(self):
        mock_db = MagicMock()
        mock_db.users.find_one_and_update = AsyncMock(return_value=None)
        with patch("app.wallet_service.get_db", return_value=mock_db):
            with self.assertRaises(HTTPException) as ctx:
                await hold_withdraw_balance(1, Decimal("50.00"))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "insufficient_balance")

    async def test_hold_succeeds_when_balance_available(self):
        mock_db = MagicMock()
        mock_db.users.find_one_and_update = AsyncMock(return_value={"id": 1})
        with patch("app.wallet_service.get_db", return_value=mock_db):
            await hold_withdraw_balance(1, Decimal("10.00"))
        mock_db.users.find_one_and_update.assert_awaited_once()


class ProductionSecretsTests(unittest.TestCase):
    def test_production_requires_admin_hashes(self):
        os.environ["NODE_ENV"] = "production"
        os.environ["ADMIN_LOGIN"] = "secure_admin"
        os.environ["ADMIN_PIN_HASH"] = ""
        os.environ["ADMIN_PASSWORD_HASH"] = ""
        os.environ["INTERNAL_SECRET"] = "long-enough-secret-here-32"
        os.environ["BLIK_VERIFY_STRICT"] = "true"
        from app.config import get_settings
        from app.safe_url import validate_production_secrets

        get_settings.cache_clear()
        with self.assertRaises(RuntimeError) as ctx:
            validate_production_secrets()
        self.assertIn("ADMIN_PIN_HASH", str(ctx.exception))
        os.environ["NODE_ENV"] = "development"
        get_settings.cache_clear()

    def test_production_rejects_example_internal_secret(self):
        os.environ["NODE_ENV"] = "production"
        os.environ["ADMIN_LOGIN"] = "secure_admin"
        os.environ["ADMIN_PIN_HASH"] = "$argon2id$v=19$m=65536,t=3,p=1$fake"
        os.environ["ADMIN_PASSWORD_HASH"] = "$argon2id$v=19$m=65536,t=3,p=1$fake"
        os.environ["INTERNAL_SECRET"] = "change-me-to-32-random-bytes-min"
        os.environ["BLIK_VERIFY_STRICT"] = "true"
        from app.config import get_settings
        from app.safe_url import validate_production_secrets

        get_settings.cache_clear()
        with self.assertRaises(RuntimeError) as ctx:
            validate_production_secrets()
        self.assertIn("INTERNAL_SECRET", str(ctx.exception))
        os.environ["NODE_ENV"] = "development"
        get_settings.cache_clear()


class OtpLockoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_assert_locked_when_locked_until_future(self):
        from datetime import datetime, timedelta, timezone

        from app.otp_lockout import assert_otp_not_locked

        mock_db = MagicMock()
        mock_col = MagicMock()
        mock_db.otp_lockouts = mock_col
        mock_col.find_one = AsyncMock(
            return_value={
                "_id": "discord:127.0.0.1",
                "locked_until": datetime.now(timezone.utc) + timedelta(minutes=10),
            }
        )
        with patch("app.otp_lockout.get_db", return_value=mock_db):
            with self.assertRaises(HTTPException) as ctx:
                await assert_otp_not_locked("discord", "127.0.0.1")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.detail, "otp_locked")


class BlikLegacyTests(unittest.TestCase):
    def test_legacy_confirm_404_in_production(self):
        from app.config import get_settings

        os.environ["NODE_ENV"] = "production"
        get_settings.cache_clear()
        s = get_settings()
        self.assertFalse(s.is_development)
        os.environ["NODE_ENV"] = "development"
        get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
