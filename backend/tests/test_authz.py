"""Authorization helper tests."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_SECRET", "test-internal-secret-32chars")
os.environ.setdefault("NODE_ENV", "development")

from fastapi import HTTPException  # noqa: E402

from app.authz import require_admin_target_username, require_resource_owner  # noqa: E402


class AuthzTests(unittest.TestCase):
    def test_require_resource_owner_blocks_cross_user(self):
        with self.assertRaises(HTTPException) as ctx:
            require_resource_owner(2, 1)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_require_resource_owner_allows_match(self):
        require_resource_owner(5, 5)

    def test_require_admin_target_username_normalizes(self):
        self.assertEqual(require_admin_target_username("Player_One"), "player_one")

    def test_require_admin_target_username_rejects_bad(self):
        with self.assertRaises(HTTPException):
            require_admin_target_username("not valid!")


if __name__ == "__main__":
    unittest.main()
