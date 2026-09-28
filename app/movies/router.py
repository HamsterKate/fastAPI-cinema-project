from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import require_roles
from app.accounts.models import UserGroupEnum, UserModel
from app.db.session import get_db
from app.movies.models import MovieStatusEnum
from app.movies.schemas import (
    MovieCreateRequestSchema,
    MovieCreateResponseSchema,
    MovieDetailSchema,
    MovieListResponseSchema,
    MovieUpdateRequestSchema,
)
from app.movies.services import (
    ActorNotFoundError,
    AmbiguousActorError,
    CatalogConflictError,
    create_movie,
    get_movies_page,
    get_movie_detail,
    update_movie,
    MovieNotFoundError,
    delete_movie,
)
from app.movies.validators import normalize_country_code, is_valid_country_code

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get(
    "",
    response_model=MovieListResponseSchema,
)
async def list_movies_endpoint(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    q: str | None = Query(default=None, max_length=100),
    genre: str | None = Query(default=None, max_length=255),
    country: str | None = Query(default=None, max_length=20),
    movie_status: MovieStatusEnum | None = Query(
        default=None,
        alias="status",
    ),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    country = normalize_country_code(country) if country is not None else None

    if country and not is_valid_country_code(country):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Country code must contain 2 or 3 Latin letters",
        )

    return await get_movies_page(
        db=db,
        page=page,
        per_page=per_page,
        path=request.url.path,
        q=q,
        genre=genre,
        country=country,
        movie_status=movie_status,
    )


@router.post(
    "",
    response_model=MovieCreateResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie_endpoint(
    data: MovieCreateRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(
        require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN)
    ),
) -> MovieCreateResponseSchema:
    try:
        movie, messages = await create_movie(db, data)
    except ActorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (AmbiguousActorError, CatalogConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return MovieCreateResponseSchema(
        movie=MovieDetailSchema.model_validate(movie),
        messages=messages,
    )


@router.get(
    "/{movie_id}",
    response_model=MovieDetailSchema,
)
async def get_movie_detail_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    movie = await get_movie_detail(db, movie_id)

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found",
        )

    return MovieDetailSchema.model_validate(movie)


@router.patch(
    "/{movie_id}",
    response_model=MovieDetailSchema,
)
async def update_movie_endpoint(
    movie_id: UUID,
    data: MovieUpdateRequestSchema,
    db: AsyncSession = Depends(get_db),
    _current_user: UserModel = Depends(
        require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN)
    ),
) -> MovieDetailSchema:
    try:
        movie = await update_movie(db, movie_id, data)
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CatalogConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return MovieDetailSchema.model_validate(movie)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_movie_endpoint(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: UserModel = Depends(
        require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN)
    ),
) -> None:
    try:
        await delete_movie(db, movie_id)
    except MovieNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
