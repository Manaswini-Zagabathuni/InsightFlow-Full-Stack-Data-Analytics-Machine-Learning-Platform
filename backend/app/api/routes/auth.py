from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
DUMMY_PASSWORD_HASH = hash_password("invalid-password-placeholder-1")


def normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = normalize_email(str(payload.email))
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == normalize_email(str(payload.email))))
    password_matches = verify_password(payload.password, user.password_hash if user is not None else DUMMY_PASSWORD_HASH)
    if user is None or not password_matches:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)) -> Response:
    """Validate the session; clients complete stateless JWT logout by discarding the token."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
