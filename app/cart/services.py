from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.repository import CartRepository
from app.cart.schemas import CartItemResponseSchema, CartResponseSchema


class CartMovieNotFoundError(Exception):
    pass


class CartItemAlreadyExistsError(Exception):
    pass


class CartItemNotFoundError(Exception):
    pass


def build_cart_response(cart) -> CartResponseSchema:
    items = sorted(
        cart.items,
        key=lambda item: item.added_at,
    )
    total_price = sum(
        (item.movie.price for item in items),
        start=Decimal("0.00"),
    )

    return CartResponseSchema(
        id=cart.id,
        items=[CartItemResponseSchema.model_validate(item) for item in items],
        total_items=len(items),
        total_price=total_price,
    )


async def get_or_create_cart(
    repository: CartRepository,
    user_id: UUID,
):
    cart = await repository.get_cart_by_user_id(user_id)

    if cart is None:
        cart = await repository.create_cart(user_id)

    return cart


async def get_cart(
    db: AsyncSession,
    user_id: UUID,
) -> CartResponseSchema:
    repository = CartRepository(db)
    cart = await get_or_create_cart(repository, user_id)
    await db.commit()

    saved_cart = await repository.get_cart_by_user_id(user_id)
    assert saved_cart is not None

    return build_cart_response(saved_cart)


async def add_movie_to_cart(
    db: AsyncSession,
    user_id: UUID,
    movie_id: UUID,
) -> CartResponseSchema:
    repository = CartRepository(db)
    cart = await get_or_create_cart(repository, user_id)

    movie = await repository.get_available_movie_by_id(movie_id)
    if movie is None:
        raise CartMovieNotFoundError("Movie not found")

    existing_item = await repository.get_item(cart.id, movie_id)
    if existing_item is not None:
        raise CartItemAlreadyExistsError("Movie is already in the cart")

    try:
        await repository.add_item(cart.id, movie_id)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise CartItemAlreadyExistsError("Movie is already in the cart") from exc

    saved_cart = await repository.get_cart_by_user_id(user_id)
    assert saved_cart is not None

    return build_cart_response(saved_cart)


async def remove_movie_from_cart(
    db: AsyncSession,
    user_id: UUID,
    movie_id: UUID,
) -> CartResponseSchema:
    repository = CartRepository(db)
    cart = await repository.get_cart_by_user_id(user_id)

    if cart is None:
        raise CartItemNotFoundError("Movie is not in the cart")

    item = await repository.get_item(cart.id, movie_id)
    if item is None:
        raise CartItemNotFoundError("Movie is not in the cart")

    await repository.delete_item(item)
    await db.commit()

    saved_cart = await repository.get_cart_by_user_id(user_id)
    assert saved_cart is not None

    return build_cart_response(saved_cart)


async def clear_cart(
    db: AsyncSession,
    user_id: UUID,
) -> CartResponseSchema:
    repository = CartRepository(db)
    cart = await get_or_create_cart(repository, user_id)

    await repository.clear_items(cart.id)
    await db.commit()

    saved_cart = await repository.get_cart_by_user_id(user_id)
    assert saved_cart is not None

    return build_cart_response(saved_cart)
