"""Tests for MongoDB operator rejection."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "mongodb://localhost:27017")
os.environ.setdefault("INTERNAL_SECRET", "test-internal-secret-32chars")
os.environ.setdefault("NODE_ENV", "development")

from fastapi import HTTPException  # noqa: E402

from app.mongo_sanitize import reject_operators  # noqa: E402


class MongoSanitizeTests(unittest.TestCase):
    def test_rejects_dollar_key(self):
        with self.assertRaises(HTTPException):
            reject_operators({"$gt": 1})

    def test_rejects_nested_operator(self):
        with self.assertRaises(HTTPException):
            reject_operators({"payload": {"$where": "1"}})

    def test_allows_plain_dict(self):
        reject_operators({"names": ["a"], "imageUrl": "https://czutkabet.com/x.png"})


if __name__ == "__main__":
    unittest.main()
