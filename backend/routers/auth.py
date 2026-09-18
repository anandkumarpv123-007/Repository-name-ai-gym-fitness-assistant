from models.user import User
from fastapi import APIRouter, Depends, HTTPException , Form
from sqlalchemy.orm import Session

from database import SessionLocal
from schemas.auth import UserLogin, UserRegister, UserProfileUpdate
from auth.security import hash_password, verify_password
from auth.token import create_access_token, verify_access_token
from fastapi.security import OAuth2PasswordBearer


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
):
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

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "date_of_birth": current_user.date_of_birth,
        "gender": current_user.gender,
        "height_cm": current_user.height_cm,
        "weight_kg": current_user.weight_kg,
        "fitness_goal": current_user.fitness_goal,
        "activity_level": current_user.activity_level,
        "dietary_preference": current_user.dietary_preference
    }

@router.put("/profile")
def update_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.date_of_birth = profile.date_of_birth
    current_user.gender = profile.gender
    current_user.height_cm = profile.height_cm
    current_user.weight_kg = profile.weight_kg
    current_user.fitness_goal = profile.fitness_goal
    current_user.activity_level = profile.activity_level
    current_user.dietary_preference = profile.dietary_preference

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "profile": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "date_of_birth": current_user.date_of_birth,
            "gender": current_user.gender,
            "height_cm": current_user.height_cm,
            "weight_kg": current_user.weight_kg,
            "fitness_goal": current_user.fitness_goal,
            "activity_level": current_user.activity_level,
            "dietary_preference": current_user.dietary_preference
        }
    }
