from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.services import activate_user
from app.db.session import get_db


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
