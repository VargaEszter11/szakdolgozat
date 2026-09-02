from typing import Any, List, Optional, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import crud, schemas, get_db, models
from utils.auth_deps import current_user_id, get_current_user
from utils.feedback_image_upload import save_feedback_image

router = APIRouter()


def _feedback_response(db: Session, row: Any, user: Optional[Any] = None) -> schemas.FeedbackResponse:
    if user is None:
        user = crud.get_user(db, int(row.user_id))
    user_any = cast(Any, user) if user is not None else None
    return schemas.FeedbackResponse(
        id=int(row.id),
        user_id=int(row.user_id),
        username=str(user_any.username) if user_any else f"user#{row.user_id}",
        email=str(user_any.email) if user_any and user_any.email else None,
        message=str(row.message),
        image_path=row.image_path,
        solved=bool(getattr(row, "solved", False)),
        created_at=row.created_at,
    )


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
    return _feedback_response(db, row, user)


@router.get("/feedback/mine", response_model=List[schemas.FeedbackResponse])
def list_my_feedback(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user = cast(Any, current_user)
    rows = crud.list_feedbacks_for_user(db, user_id=current_user_id(current_user))
    return [_feedback_response(db, cast(Any, row), user) for row in rows]
