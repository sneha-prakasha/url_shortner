"""Signup, login, and "who am I"."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..ratelimit import rate_limit
from ..schemas import Credentials, TokenOut, UserOut
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

auth_limit = Depends(rate_limit("auth", settings.AUTH_LIMIT_PER_MIN))


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id),
        user=UserOut(id=user.id, email=user.email),
    )


@router.post("/signup", response_model=TokenOut, status_code=201, dependencies=[auth_limit])
def signup(payload: Credentials, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two signups at the same moment
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    return _token_response(user)


@router.post("/login", response_model=TokenOut, dependencies=[auth_limit])
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Same message for "no such user" and "wrong password" so attackers learn nothing
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email)
