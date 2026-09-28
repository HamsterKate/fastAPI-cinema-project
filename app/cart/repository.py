from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cart.models import CartItemModel, CartModel
from app.movies.models import MovieModel


class CartRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_cart_by_user_id(
        self,
        user_id: UUID,
    ) -> CartModel | None:
        statement = (
            select(CartModel)
            .options(
                selectinload(CartModel.items)
                .selectinload(CartItemModel.movie)
                .selectinload(MovieModel.genres),
            )
            .where(CartModel.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def create_cart(self, user_id: UUID) -> CartModel:
        cart = CartModel(user_id=user_id)
        self.db.add(cart)
        await self.db.flush()
        return cart

    async def get_available_movie_by_id(
        self,
        movie_id: UUID,
    ) -> MovieModel | None:
        statement = select(MovieModel).where(
            MovieModel.id == movie_id,
            MovieModel.deleted_at.is_(None),
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_item(
        self,
        cart_id: UUID,
        movie_id: UUID,
    ) -> CartItemModel | None:
        statement = select(CartItemModel).where(
            CartItemModel.cart_id == cart_id,
            CartItemModel.movie_id == movie_id,
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def add_item(
        self,
        cart_id: UUID,
        movie_id: UUID,
    ) -> CartItemModel:
        item = CartItemModel(
            cart_id=cart_id,
            movie_id=movie_id,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: CartItemModel) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def clear_items(self, cart_id: UUID) -> None:
        await self.db.execute(
            delete(CartItemModel).where(
                CartItemModel.cart_id == cart_id
            )
        )
        await self.db.flush()
        