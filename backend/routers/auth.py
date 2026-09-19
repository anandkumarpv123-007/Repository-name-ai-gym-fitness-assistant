from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import SessionLocal
from models.user import User
from models.profile import Profile
from schemas.auth import UserRegister, UserProfileUpdate
from auth.security import hash_password, verify_password
from auth.token import create_access_token, verify_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    user_id = verify_access_token(token)

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def serialize_user_profile(user: User) -> dict:
    """Helper to serialize user account and profile data using user.profile."""
    profile = user.profile
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "date_of_birth": profile.date_of_birth if profile else None,
        "gender": profile.gender if profile else None,
        "height_cm": profile.height_cm if profile else None,
        "weight_kg": profile.weight_kg if profile else None,
        "fitness_goal": profile.fitness_goal if profile else None,
        "activity_level": profile.activity_level if profile else None,
        "dietary_preference": profile.dietary_preference if profile else None
    }


def update_or_create_user_profile(
    user: User,
    profile_data: UserProfileUpdate,
    db: Session
) -> dict:
    """Helper to update an existing Profile or create a new one linked to user."""
    profile = user.profile
    if profile is None:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    update_fields = profile_data.model_dump(exclude_unset=True)

    if profile is None:
        profile = Profile(user_id=user.id, **update_fields)
        db.add(profile)
    else:
        for field, value in update_fields.items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "profile": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "date_of_birth": profile.date_of_birth,
            "gender": profile.gender,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "fitness_goal": profile.fitness_goal,
            "activity_level": profile.activity_level,
            "dietary_preference": profile.dietary_preference
        }
    }


@router.post("/register")
def register_user(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    hashed_password = hash_password(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }


@router.post("/login")
def login_user(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.email == username)
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_is_correct = verify_password(
        password,
        existing_user.password_hash
    )

    if not password_is_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(existing_user.id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }


# Compatibility alias: GET /auth/me
@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return serialize_user_profile(current_user)


# Compatibility alias: PUT /auth/profile
@router.put("/profile")
def update_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_or_create_user_profile(current_user, profile, db)
