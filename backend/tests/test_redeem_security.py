"""Promo code and credential generation hardening."""
from __future__ import annotations

import os
import re
import unittest

os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_SECRET", "test-internal-secret-32chars")
os.environ.setdefault("NODE_ENV", "development")

from app.security import (  # noqa: E402
    generate_daily_reward_code,
    generate_nick_reward_code,
    generate_pass_key,
    generate_password,
)


class CredentialGenerationTests(unittest.TestCase):
    def test_daily_code_has_high_entropy_suffix(self):
        code = generate_daily_reward_code()
        self.assertTrue(code.startswith("DAILY_"))
        suffix = code[6:]
        self.assertEqual(len(suffix), 16)
        self.assertTrue(re.fullmatch(r"[0-9A-F]{16}", suffix))

    def test_nick_code_has_high_entropy_suffix(self):
        code = generate_nick_reward_code()
        self.assertTrue(code.startswith("DISCORD_"))
        suffix = code[8:]
        self.assertEqual(len(suffix), 16)
        self.assertTrue(re.fullmatch(r"[0-9A-F]{16}", suffix))

    def test_password_and_pass_key_are_urlsafe_tokens(self):
        for _ in range(10):
            pw = generate_password()
            pk = generate_pass_key()
            self.assertGreaterEqual(len(pw), 16)
            self.assertGreaterEqual(len(pk), 24)
            self.assertNotIn(" ", pw)
            self.assertNotIn(" ", pk)


if __name__ == "__main__":
    unittest.main()
