from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.payments.models import PaymentStatusEnum


class PaymentCheckoutResponseSchema(BaseModel):
    payment_id: UUID
    order_id: UUID
    checkout_url: str
    status: PaymentStatusEnum


class PaymentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: PaymentStatusEnum
    amount: str
    currency: str
    stripe_checkout_session_id: str
