from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.cart.schemas import CartResponseSchema
from app.cart.services import (
    CartItemAlreadyExistsError,
    CartItemNotFoundError,
    CartMovieNotFoundError,
    add_movie_to_cart,
    clear_cart,
    get_cart,
    remove_movie_from_cart,
)
from app.db.session import get_db


router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)


@router.get(
    "",
    response_model=CartResponseSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
    },
)
async def get_cart_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CartResponseSchema:
    return await get_cart(db, current_user.id)


@router.post(
    "/items/{movie_id}",
    response_model=CartResponseSchema,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Invalid or expired access token"},
        404: {"description": "Movie not found"},
        409: {"description": "Movie is already in the cart"},
    },
)
async def add_cart_item_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CartResponseSchema:
    try:
        return await add_movie_to_cart(
            db,
            current_user.id,
            movie_id,
        )
    except CartMovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CartItemAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/items/{movie_id}",
    response_model=CartResponseSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
        404: {"description": "Movie is not in the cart"},
    },
)
async def remove_cart_item_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CartResponseSchema:
    try:
        return await remove_movie_from_cart(
            db,
            current_user.id,
            movie_id,
        )
    except CartItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/items",
    response_model=CartResponseSchema,
    responses={
        401: {"description": "Invalid or expired access token"},
    },
)
async def clear_cart_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CartResponseSchema:
    return await clear_cart(db, current_user.id)
