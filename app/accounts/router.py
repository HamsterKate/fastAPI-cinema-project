from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.services import (
    activate_user,
    resend_activation,
)
from app.db.session import get_db
from app.accounts.schemas import ResendActivationSchema

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
