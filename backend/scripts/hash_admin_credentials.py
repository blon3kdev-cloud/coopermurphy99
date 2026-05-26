#!/usr/bin/env python3
"""Print Argon2 hashes for ADMIN_PIN_HASH and ADMIN_PASSWORD_HASH."""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.security import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Hash admin PIN and password for .env")
    parser.add_argument("--pin", help="PIN (else prompt)")
    parser.add_argument("--password", help="Password (else prompt)")
    args = parser.parse_args()
    pin = args.pin or getpass.getpass("Admin PIN: ")
    password = args.password or getpass.getpass("Admin password: ")
    if not pin or not password:
        print("PIN and password required", file=sys.stderr)
        sys.exit(1)
    print(f"ADMIN_PIN_HASH={hash_password(pin)}")
    print(f"ADMIN_PASSWORD_HASH={hash_password(password)}")


if __name__ == "__main__":
    main()
