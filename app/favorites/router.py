from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.models import UserModel
from app.db.session import get_db
from app.favorites.services import (
    FavoriteAlreadyExistsError,
    FavoriteMovieNotFoundError,
    FavoriteNotFoundError,
    add_favorite,
    get_favorites_page,
    remove_favorite,
)
from app.movies.schemas import MovieListResponseSchema


router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=MovieListResponseSchema)
async def list_favorites_endpoint(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> MovieListResponseSchema:
    return await get_favorites_page(
        db, current_user.id, page, per_page
    )


@router.post("/{movie_id}", status_code=status.HTTP_201_CREATED)
async def add_favorite_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, str]:
    try:
        await add_favorite(db, current_user.id, movie_id)
    except FavoriteMovieNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Movie not found"
        ) from exc
    except FavoriteAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409, detail="Movie is already in favorites"
        ) from exc

    return {"message": "Movie added to favorites"}


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    try:
        await remove_favorite(db, current_user.id, movie_id)
    except FavoriteNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Favorite not found"
        ) from exc
