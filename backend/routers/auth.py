from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from database import crud, schemas, get_db
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from typing import Any, cast
from utils.email import send_password_reset_email
import os

router = APIRouter()


def get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _public_base_url(request: Request) -> str:
    override = os.getenv("PUBLIC_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.post("/register", response_model=schemas.RegisterResponse)
def register(request: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username already exists
    existing_user = crud.get_user_by_username(db, username=request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = crud.get_user_by_email(db, email=request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the user
    user_data = schemas.UserCreate(
        username=request.username,
        email=request.email,
        password=request.password
    )
    crud.create_user(db=db, user=user_data)
    
    return schemas.RegisterResponse(
        success=True,
        message="User registered successfully"
    )


@router.post("/login", response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return login info"""
    # Get user by username
    user = crud.get_user_by_username(db, username=request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    user_row = cast(Any, user)
    
    # Verify password
    if not crud.verify_password(request.password, user_row.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return schemas.LoginResponse(
        success=True,
        user_id=user_row.id,
        username=user_row.username,
    )


@router.post("/google-login", response_model=schemas.LoginResponse)
def google_login(request: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    """Authenticate or create a user via Google ID token."""
    google_client_id = get_google_client_id()

    if not google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google sign-in is not configured on the server"
        )

    try:
        id_info = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            google_client_id
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )

    if not id_info.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified"
        )

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide an email"
        )

    user = crud.get_user_by_email(db, email=email)
    if not user:
        user = crud.create_google_user(
            db=db,
            email=email,
            display_name=id_info.get("name"),
        )
    user_row = cast(Any, user)

    return schemas.LoginResponse(
        success=True,
        user_id=user_row.id,
        username=user_row.username,
    )


@router.get("/google-config")
def google_config():
    """Expose public Google OAuth configuration to frontend."""
    return {
        "client_id": get_google_client_id()
    }


_FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "If an account with that email exists, we've sent a password reset link to it."
)


@router.post("/forgot-password/request", response_model=schemas.ForgotPasswordRequestResponse)
def forgot_password_request(
    request: schemas.ForgotPasswordRequest, http_request: Request, db: Session = Depends(get_db)
):
    """Email a password reset link if the address belongs to an account.

    Always responds with the same generic message regardless of whether the
    email is registered, so this endpoint can't be used to enumerate accounts.
    """
    user = crud.get_user_by_email(db, email=request.email)
    if user:
        user_row = cast(Any, user)
        raw_token = crud.create_password_reset_token(db, user_id=user_row.id)
        reset_url = f"{_public_base_url(http_request)}/reset-password?token={raw_token}"
        send_password_reset_email(
            user_row.email, reset_url, crud.PASSWORD_RESET_TOKEN_TTL_MINUTES
        )

    return schemas.ForgotPasswordRequestResponse(
        success=True, message=_FORGOT_PASSWORD_GENERIC_MESSAGE
    )


@router.post("/forgot-password/reset", response_model=schemas.ForgotPasswordResetResponse)
def forgot_password_reset(request: schemas.ForgotPasswordResetRequest, db: Session = Depends(get_db)):
    """Reset a password using a token issued by /forgot-password/request."""
    token_row = crud.get_valid_password_reset_token(db, raw_token=request.token)
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        )

    token_row_data = cast(Any, token_row)
    updated_user = crud.update_user_password(
        db, user_id=token_row_data.user_id, new_password=request.new_password
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    crud.consume_password_reset_token(db, token_row)

    return schemas.ForgotPasswordResetResponse(success=True, message="Password reset successfully")
