from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.payments.models import PaymentModel


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payment: PaymentModel) -> PaymentModel:
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_by_checkout_session_id(
        self,
        checkout_session_id: str,
    ) -> PaymentModel | None:
        result = await self.db.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.order))
            .where(PaymentModel.stripe_checkout_session_id == checkout_session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: UUID) -> list[PaymentModel]:
        result = await self.db.execute(
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.created_at.desc())
        )
        return list(result.scalars().all())
