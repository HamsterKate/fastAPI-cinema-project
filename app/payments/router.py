import stripe

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.core.config import settings
from app.db.session import get_db
from app.payments.schemas import PaymentCheckoutResponseSchema
from app.payments.service import (
    OrderCannotBePaidError,
    OrderNotFoundForPaymentError,
    StripeCheckoutError,
    create_checkout_session,
    mark_payment_succeeded,
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


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid webhook payload or signature"},
        503: {"description": "Stripe webhook is not configured"},
    },
)
async def stripe_webhook_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook is not configured",
        )

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if signature is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook payload",
        ) from exc
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature",
        ) from exc

    if event["type"] == "checkout.session.completed":
        await mark_payment_succeeded(
            db,
            event["data"]["object"].to_dict(),
        )

    return {"received": True}
