"""Shared password strength rules for registration, profile update, and reset."""

from __future__ import annotations

import re

PASSWORD_MIN_LENGTH = 8

PASSWORD_REQUIREMENTS_MESSAGE = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a lowercase letter, a number, and a special character."
)

_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_DIGIT = re.compile(r"[0-9]")
_HAS_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def is_strong_password(password: str) -> bool:
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return False
    if not _HAS_UPPER.search(password):
        return False
    if not _HAS_LOWER.search(password):
        return False
    if not _HAS_DIGIT.search(password):
        return False
    if not _HAS_SPECIAL.search(password):
        return False
    return True


def validate_password_strength(password: str) -> str:
    if not is_strong_password(password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    return password
