"""Tests for URL and username validators."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_SECRET", "test-internal-secret-32chars")
os.environ.setdefault("NODE_ENV", "development")

from app.safe_url import (  # noqa: E402
    normalize_username,
    safe_image_url,
    validate_production_secrets,
)


class SafeUrlTests(unittest.TestCase):
    def test_normalize_username_valid(self):
        self.assertEqual(normalize_username("Player_One"), "player_one")

    def test_normalize_username_rejects_invalid(self):
        self.assertIsNone(normalize_username("bad regex ("))
        self.assertIsNone(normalize_username("ab"))

    def test_safe_image_url_rejects_javascript(self):
        self.assertIsNone(safe_image_url("javascript:alert(1)"))

    def test_safe_image_url_rejects_invalid_data_uri(self):
        self.assertIsNone(safe_image_url("data:text/plain;base64,abc"))

    def test_safe_image_url_accepts_preset_data_uri(self):
        payload = "data:image/jpeg;base64," + ("a" * 32)
        self.assertEqual(safe_image_url(payload), payload)

    def test_safe_image_url_accepts_https_czutkabet(self):
        self.assertEqual(
            safe_image_url("https://czutkabet.com/uploads/x.png"),
            "https://czutkabet.com/uploads/x.png",
        )

    def test_validate_production_secrets_allows_dev_defaults(self):
        os.environ["NODE_ENV"] = "development"
        from app.config import get_settings

        get_settings.cache_clear()
        validate_production_secrets()

    def test_validate_production_secrets_rejects_default_login(self):
        os.environ["NODE_ENV"] = "production"
        os.environ["ADMIN_LOGIN"] = "jrm8"
        os.environ["ADMIN_PIN_HASH"] = "$argon2id$v=19$m=65536,t=3,p=1$fake"
        os.environ["ADMIN_PASSWORD_HASH"] = "$argon2id$v=19$m=65536,t=3,p=1$fake"
        os.environ["INTERNAL_SECRET"] = "long-enough-secret-here-32chars"
        os.environ["BLIK_VERIFY_STRICT"] = "true"
        from app.config import get_settings

        get_settings.cache_clear()
        with self.assertRaises(RuntimeError):
            validate_production_secrets()
        os.environ["NODE_ENV"] = "development"
        get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
