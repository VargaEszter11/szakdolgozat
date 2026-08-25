"""JWT access-token helpers and FastAPI auth dependency."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import crud, get_db, models

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7

security = HTTPBearer(auto_error=False)


def jwt_secret() -> str:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    if secret:
        return secret
    # Local/thesis fallback; set JWT_SECRET in production.
    return "dev-insecure-jwt-secret-change-me"


def create_access_token(*, user_id: int, username: str) -> str:
    """Issue a signed JWT used by the frontend as Bearer access_token."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=ALGORITHM)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    """FastAPI dependency: require a valid Bearer JWT and load the user."""
    if creds is None or not (creds.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            creds.credentials,
            jwt_secret(),
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def current_user_id(user: models.User) -> int:
    return int(cast(Any, user).id)


def require_self(user_id: int, current_user: models.User) -> None:
    """Reject if the path user_id is not the authenticated user."""
    if current_user_id(current_user) != int(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
