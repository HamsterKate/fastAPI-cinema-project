import asyncio

import pytest
import stripe

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.orders.models import OrderModel, OrderStatusEnum
from app.payments.models import PaymentModel, PaymentStatusEnum
from app.payments.repository import PaymentRepository
from app.payments.schemas import PaymentCheckoutResponseSchema


class OrderNotFoundForPaymentError(Exception):
    pass


class OrderCannotBePaidError(Exception):
    pass


class StripeCheckoutError(Exception):
    pass


def price_to_cents(price: Decimal) -> int:
    return int(
        (price * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


async def get_order_for_checkout(
    db: AsyncSession,
    order_id: UUID,
    user_id: UUID,
) -> OrderModel | None:
    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(
            OrderModel.id == order_id,
            OrderModel.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_checkout_session(
    db: AsyncSession,
    order_id: UUID,
    user_id: UUID,
    customer_email: str,
) -> PaymentCheckoutResponseSchema:
    order = await get_order_for_checkout(db, order_id, user_id)

    if order is None:
        raise OrderNotFoundForPaymentError("Order not found")

    if order.status is not OrderStatusEnum.PENDING:
        raise OrderCannotBePaidError("Only pending orders can be paid")

    stripe_client = stripe.StripeClient(settings.stripe_secret_key)

    line_items = [
        {
            "price_data": {
                "currency": settings.stripe_currency,
                "product_data": {
                    "name": item.movie_name,
                },
                "unit_amount": price_to_cents(item.unit_price),
            },
            "quantity": 1,
        }
        for item in order.items
    ]

    try:
        checkout_session = await asyncio.to_thread(
            stripe_client.v1.checkout.sessions.create,
            params={
                "mode": "payment",
                "client_reference_id": str(order.id),
                "customer_email": customer_email,
                "success_url": settings.stripe_success_url,
                "cancel_url": settings.stripe_cancel_url,
                "metadata": {
                    "order_id": str(order.id),
                },
                "line_items": line_items,
            },
        )
    except stripe.StripeError as error:
        raise StripeCheckoutError("Could not create Stripe Checkout session") from error

    if checkout_session.url is None:
        raise StripeCheckoutError("Stripe did not return a checkout URL")

    payment = PaymentModel(
        order_id=order.id,
        stripe_checkout_session_id=checkout_session.id,
        status=PaymentStatusEnum.PENDING,
        amount=order.total_price,
        currency=settings.stripe_currency,
    )

    repository = PaymentRepository(db)
    await repository.create(payment)
    await db.commit()

    return PaymentCheckoutResponseSchema(
        payment_id=payment.id,
        order_id=order.id,
        checkout_url=checkout_session.url,
        status=payment.status,
    )


async def mark_payment_succeeded(
    db: AsyncSession,
    checkout_session: dict[str, object],
) -> None:
    if checkout_session.get("payment_status") != "paid":
        return

    checkout_session_id = str(checkout_session["id"])

    repository = PaymentRepository(db)
    payment = await repository.get_by_checkout_session_id(checkout_session_id)

    if payment is None:
        return

    if payment.status is PaymentStatusEnum.SUCCEEDED:
        return

    payment.status = PaymentStatusEnum.SUCCEEDED
    payment.paid_at = datetime.now(timezone.utc)

    payment_intent_id = checkout_session.get("payment_intent")
    if payment_intent_id is not None:
        payment.stripe_payment_intent_id = str(payment_intent_id)

    if payment.order.status is OrderStatusEnum.PENDING:
        payment.order.status = OrderStatusEnum.PAID

    await db.commit()
