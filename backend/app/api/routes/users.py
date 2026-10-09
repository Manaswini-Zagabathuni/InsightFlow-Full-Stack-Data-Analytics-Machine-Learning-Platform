from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)) -> User:
    return user
