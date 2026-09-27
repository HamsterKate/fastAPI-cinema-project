from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.db.session import get_db
from app.payments.schemas import PaymentCheckoutResponseSchema
from app.payments.service import (
    OrderCannotBePaidError,
    OrderNotFoundForPaymentError,
    StripeCheckoutError,
    create_checkout_session,
)


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


@router.post(
    "/orders/{order_id}/checkout",
    response_model=PaymentCheckoutResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Invalid or expired access token"},
        404: {"description": "Order not found"},
        409: {"description": "Only pending orders can be paid"},
        502: {"description": "Stripe Checkout is unavailable"},
    },
)
async def create_checkout_session_endpoint(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> PaymentCheckoutResponseSchema:
    try:
        return await create_checkout_session(
            db=db,
            order_id=order_id,
            user_id=current_user.id,
            customer_email=current_user.email,
        )
    except OrderNotFoundForPaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OrderCannotBePaidError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except StripeCheckoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
