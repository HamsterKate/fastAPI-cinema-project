from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import require_roles
from app.accounts.models import UserGroupEnum, UserModel
from app.db.session import get_db
from app.movies.schemas import (
    MovieCreateRequestSchema,
    MovieCreateResponseSchema,
    MovieDetailSchema,
    MovieListResponseSchema,
)
from app.movies.services import (
    ActorNotFoundError,
    AmbiguousActorError,
    CatalogConflictError,
    create_movie,
    get_movies_page, get_movie_detail,
)


router = APIRouter(prefix="/movies", tags=["movies"])


@router.get(
    "",
    response_model=MovieListResponseSchema,
)
async def list_movies_endpoint(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    return await get_movies_page(
        db=db,
        page=page,
        per_page=per_page,
        path=request.url.path,
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
