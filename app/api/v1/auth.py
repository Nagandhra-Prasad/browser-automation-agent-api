from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.core.dependencies import get_current_user_id
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter()


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        onboarding_completed=user.get("onboarding_completed", False),
        is_active=user.get("is_active", True),
        created_at=user["created_at"],
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate) -> TokenResponse:
    settings = get_settings()
    role = body.role

    if role == "admin":
        if not body.admin_code or body.admin_code != settings.admin_registration_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin registration code",
            )
    else:
        role = "user"

    repo = UserRepository()
    existing = await repo.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await repo.create(body.name, body.email, hash_password(body.password), role=role)
    token = create_access_token(user["id"], extra={"role": user["role"]})
    return TokenResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin) -> TokenResponse:
    repo = UserRepository()
    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator.",
        )

    token = create_access_token(user["id"], extra={"role": user["role"]})
    return TokenResponse(access_token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
async def me(user_id: str = Depends(get_current_user_id)) -> UserResponse:
    user = await UserRepository().get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_response(user)


@router.post("/onboarding-complete", response_model=UserResponse)
async def complete_onboarding(user_id: str = Depends(get_current_user_id)) -> UserResponse:
    user = await UserRepository().set_onboarding_completed(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_response(user)
