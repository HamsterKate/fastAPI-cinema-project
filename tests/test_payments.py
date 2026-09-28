from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace

import pytest

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from app.payments.service import (
    OrderCannotBePaidError,
    create_checkout_session,
    mark_payment_succeeded,
    price_to_cents,
)
from app.orders.models import OrderStatusEnum
from app.payments.models import PaymentStatusEnum


@pytest.mark.parametrize(
    ("price", "expected_cents"),
    [
        (Decimal("0.01"), 1),
        (Decimal("9.99"), 999),
        (Decimal("10.00"), 1000),
        (Decimal("9.995"), 1000),
    ],
)
def test_price_to_cents(
    price: Decimal,
    expected_cents: int,
) -> None:
    assert price_to_cents(price) == expected_cents


def test_payment_checkout_requires_access_token(
    client: TestClient,
) -> None:
    response = client.post(
        f"/api/v2/payments/orders/{uuid4()}/checkout",
    )

    assert response.status_code == 401


def test_payment_checkout_rejects_missing_order(
    client: TestClient,
    active_user: dict[str, str],
) -> None:
    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }

    response = client.post(
        f"/api/v2/payments/orders/{uuid4()}/checkout",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


@pytest.mark.asyncio
async def test_create_checkout_session_creates_pending_payment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order_id = uuid4()
    order = SimpleNamespace(
        id=order_id,
        status=OrderStatusEnum.PENDING,
        total_price=Decimal("9.99"),
        items=[
            SimpleNamespace(
                movie_name="Test movie",
                unit_price=Decimal("9.99"),
            ),
        ],
    )

    async def fake_get_order_for_checkout(
        db: object,
        order_id: object,
        user_id: object,
    ) -> object:
        return order

    created_payments = []

    class FakePaymentRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def create(self, payment: object) -> None:
            payment.id = uuid4()
            created_payments.append(payment)

    class FakeStripeClient:
        class v1:
            class checkout:
                class sessions:
                    @staticmethod
                    def create(
                        params: dict,
                    ) -> SimpleNamespace:
                        return SimpleNamespace(
                            id="cs_test_123",
                            url="https://checkout.stripe.test/session",
                        )

    fake_db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.payments.service.get_order_for_checkout",
        fake_get_order_for_checkout,
    )
    monkeypatch.setattr(
        "app.payments.service.PaymentRepository",
        FakePaymentRepository,
    )
    monkeypatch.setattr(
        "app.payments.service.stripe.StripeClient",
        lambda secret_key: FakeStripeClient(),
    )

    response = await create_checkout_session(
        db=fake_db,
        order_id=order_id,
        user_id=uuid4(),
        customer_email="user@example.com",
    )

    assert response.order_id == order_id
    assert response.checkout_url == "https://checkout.stripe.test/session"
    assert response.status is PaymentStatusEnum.PENDING
    assert len(created_payments) == 1
    assert created_payments[0].stripe_checkout_session_id == "cs_test_123"
    assert created_payments[0].amount == Decimal("9.99")
    fake_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_payment_succeeded_updates_payment_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = SimpleNamespace(
        status=PaymentStatusEnum.PENDING,
        paid_at=None,
        stripe_payment_intent_id=None,
        order=SimpleNamespace(status=OrderStatusEnum.PENDING),
    )

    class FakePaymentRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_checkout_session_id(
            self,
            checkout_session_id: str,
        ) -> object:
            assert checkout_session_id == "cs_test_123"
            return payment

    fake_db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.payments.service.PaymentRepository",
        FakePaymentRepository,
    )

    await mark_payment_succeeded(
        fake_db,
        {
            "id": "cs_test_123",
            "payment_status": "paid",
            "payment_intent": "pi_test_123",
        },
    )

    assert payment.status is PaymentStatusEnum.SUCCEEDED
    assert payment.paid_at is not None
    assert payment.stripe_payment_intent_id == "pi_test_123"
    assert payment.order.status is OrderStatusEnum.PAID
    fake_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_payment_succeeded_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = SimpleNamespace(
        status=PaymentStatusEnum.SUCCEEDED,
        order=SimpleNamespace(status=OrderStatusEnum.PAID),
    )

    class FakePaymentRepository:
        def __init__(self, db: object) -> None:
            self.db = db

        async def get_by_checkout_session_id(
            self,
            checkout_session_id: str,
        ) -> object:
            return payment

    fake_db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        "app.payments.service.PaymentRepository",
        FakePaymentRepository,
    )

    await mark_payment_succeeded(
        fake_db,
        {
            "id": "cs_test_123",
            "payment_status": "paid",
        },
    )

    assert payment.status is PaymentStatusEnum.SUCCEEDED
    fake_db.commit.assert_not_awaited()


def test_webhook_rejects_request_without_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.payments.router.settings.stripe_webhook_secret",
        "whsec_test",
    )

    response = client.post(
        "/api/v2/payments/webhook",
        content=b"{}",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing Stripe-Signature header"


def test_payment_checkout_returns_conflict_for_non_pending_order(
    client: TestClient,
    active_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create_checkout_session(
        **kwargs: object,
    ) -> object:
        raise OrderCannotBePaidError("Only pending orders can be paid")

    monkeypatch.setattr(
        "app.payments.router.create_checkout_session",
        fake_create_checkout_session,
    )

    headers = {
        "Authorization": f"Bearer {active_user['access_token']}",
    }

    response = client.post(
        f"/api/v2/payments/orders/{uuid4()}/checkout",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only pending orders can be paid"


@pytest.mark.asyncio
async def test_checkout_rejects_non_pending_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = SimpleNamespace(
        status=OrderStatusEnum.CANCELED,
    )

    async def fake_get_order_for_checkout(
        db: object,
        order_id: object,
        user_id: object,
    ) -> object:
        return order

    monkeypatch.setattr(
        "app.payments.service.get_order_for_checkout",
        fake_get_order_for_checkout,
    )

    with pytest.raises(
        OrderCannotBePaidError,
        match="Only pending orders can be paid",
    ):
        await create_checkout_session(
            db=SimpleNamespace(),
            order_id=uuid4(),
            user_id=uuid4(),
            customer_email="user@example.com",
        )
