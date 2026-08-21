from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import crud, schemas, get_db, models
from utils.auth_deps import get_current_user
from utils.feedback_image_upload import save_feedback_image

router = APIRouter()


@router.post("/feedback", response_model=schemas.FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    text = (message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Message is too long.")

    image_path = None
    if image is not None and image.filename:
        content = await image.read()
        try:
            image_path = save_feedback_image(content, image.content_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = cast(Any, current_user)
    row = cast(
        Any,
        crud.create_feedback(
            db,
            user_id=int(user.id),
            message=text,
            image_path=image_path,
        ),
    )
    return schemas.FeedbackResponse(
        id=int(row.id),
        user_id=int(row.user_id),
        username=str(user.username),
        email=str(user.email) if user.email else None,
        message=str(row.message),
        image_path=row.image_path,
        created_at=row.created_at,
    )
