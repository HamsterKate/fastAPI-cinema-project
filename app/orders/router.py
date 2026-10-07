from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.db.session import get_db
from app.orders.schemas import (
    OrderDetailSchema,
    OrderListResponseSchema,
)
from app.orders.services import (
    CartIsEmptyError,
    MovieUnavailableError,
    MoviesAlreadyPurchasedError,
    OrderCannotBeCanceledError,
    OrderNotFoundError,
    PendingOrderConflictError,
    cancel_order,
    checkout,
    get_order,
    get_orders_page,
)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.post(
    "/checkout",
    response_model=OrderDetailSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Cart is empty"},
        401: {"description": "Invalid or expired access token"},
        409: {
            "description": (
                "Movie unavailable, already purchased, "
                "or already has a pending order"
            )
        },
    },
)
async def checkout_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OrderDetailSchema:
    try:
        order = await checkout(db, current_user.id)
    except CartIsEmptyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (
        MovieUnavailableError,
        MoviesAlreadyPurchasedError,
        PendingOrderConflictError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return OrderDetailSchema.model_validate(order)


@router.get(
    "",
    response_model=OrderListResponseSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
    },
)
async def list_orders_endpoint(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OrderListResponseSchema:
    return await get_orders_page(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        path=request.url.path,
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
        404: {"description": "Order not found"},
    },
)
async def get_order_endpoint(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OrderDetailSchema:
    try:
        order = await get_order(
            db,
            current_user.id,
            order_id,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return OrderDetailSchema.model_validate(order)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderDetailSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
        404: {"description": "Order not found"},
        409: {"description": "Only pending orders can be canceled"},
    },
)
async def cancel_order_endpoint(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OrderDetailSchema:
    try:
        order = await cancel_order(
            db,
            current_user.id,
            order_id,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OrderCannotBeCanceledError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return OrderDetailSchema.model_validate(order)
