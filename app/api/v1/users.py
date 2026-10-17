from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_admin_id
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserActiveUpdate, UserResponse

router = APIRouter()


def _user_response(row: dict) -> UserResponse:
    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
        onboarding_completed=row.get("onboarding_completed", False),
        is_active=row.get("is_active", True),
        created_at=row["created_at"],
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    _admin_id: str = Depends(get_current_admin_id),
) -> list[UserResponse]:
    rows = await UserRepository().list_all()
    return [_user_response(row) for row in rows]


@router.patch("/{user_id}/active", response_model=UserResponse)
async def set_user_active(
    user_id: str,
    body: UserActiveUpdate,
    admin_id: str = Depends(get_current_admin_id),
) -> UserResponse:
    if user_id == admin_id and not body.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    repo = UserRepository()
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await repo.set_active(user_id, body.is_active)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_response(updated)
