from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.user import User
from schemas.auth import UserProfileUpdate
from routers.auth import (
    get_current_user,
    get_db,
    serialize_user_profile,
    update_or_create_user_profile,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me")
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Retrieve current authenticated user and profile information."""
    return serialize_user_profile(current_user)


@router.put("/me")
def update_current_user_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update or create profile for current authenticated user."""
    return update_or_create_user_profile(current_user, profile, db)
