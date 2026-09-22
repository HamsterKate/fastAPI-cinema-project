from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.services import (
    activate_user,
    login_user,
    register_user,
    resend_activation,
)
from app.db.session import get_db
from app.accounts.schemas import (
    ResendActivationSchema,
    TokenResponseSchema,
    UserLoginSchema,
    UserRegistrationSchema,
    UserResponseSchema,
)


router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
)


@router.get("/activate", status_code=status.HTTP_200_OK)
async def activate_account(
    token: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        await activate_user(db, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {"message": "Account activated successfully."}


@router.post("/resend-activation", status_code=status.HTTP_200_OK)
async def resend_activation_endpoint(
    data: ResendActivationSchema,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await resend_activation(db, data.email)

    return {
        "message": (
            "If your account exists and is not activated, "
            "a new activation email has been sent."
        )
    }


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email already registered"},
    },
)
async def register(
    data: UserRegistrationSchema,
    db: AsyncSession = Depends(get_db),
) -> UserResponseSchema:
    try:
        user = await register_user(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserResponseSchema.model_validate(
        user,
        from_attributes=True,
    )


@router.post(
    "/login",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Account is not activated"},
    },
)
async def login(
    data: UserLoginSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenResponseSchema:
    try:
        return await login_user(db, data)
    except ValueError as exc:
        if str(exc) == "Account is not activated.":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc
