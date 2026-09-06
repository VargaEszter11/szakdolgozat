import pytest
from pydantic import ValidationError

from backend.utils.password_policy import is_strong_password, validate_password_strength
from backend.database import schemas


@pytest.mark.parametrize(
    "password,ok",
    [
        ("Short1!", False),
        ("alllower1!", False),
        ("ALLUPPER1!", False),
        ("NoDigits!!", False),
        ("NoSpecial1", False),
        ("GoodPass1!", True),
    ],
)
def test_is_strong_password(password, ok):
    assert is_strong_password(password) is ok


def test_validate_password_strength_raises():
    with pytest.raises(ValueError):
        validate_password_strength("weak")


def test_register_request_rejects_weak_password():
    with pytest.raises(ValidationError):
        schemas.RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="weakpass",
        )
