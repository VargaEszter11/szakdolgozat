from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import crud, schemas, get_db

router = APIRouter()


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
    
    # Verify password
    if not crud.verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return schemas.LoginResponse(
        success=True,
        user_id=user.id,
        username=user.username
    )


@router.post("/forgot-password/verify", response_model=schemas.ForgotPasswordVerifyResponse)
def forgot_password_verify(request: schemas.ForgotPasswordVerifyRequest, db: Session = Depends(get_db)):
    """Verify username + email combination for password reset"""
    user = crud.get_user_by_username(db, username=request.username)
    if not user or user.email != request.email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that username and email combination"
        )

    return schemas.ForgotPasswordVerifyResponse(success=True, user_id=user.id)


@router.post("/forgot-password/reset", response_model=schemas.ForgotPasswordResetResponse)
def forgot_password_reset(request: schemas.ForgotPasswordResetRequest, db: Session = Depends(get_db)):
    """Reset password for a verified user"""
    user_update = schemas.UserUpdate(password=request.new_password)
    updated_user = crud.update_user(db, user_id=request.user_id, user_update=user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return schemas.ForgotPasswordResetResponse(success=True, message="Password reset successfully")
