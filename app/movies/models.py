from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.cart.models import CartItemModel
from app.db.models.base import Base


class MovieStatusEnum(StrEnum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


movies_genres = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        PGUUID(as_uuid=True),
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        PGUUID(as_uuid=True),
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

movies_actors = Table(
    "movies_actors",
    Base.metadata,
    Column(
        "movie_id",
        PGUUID(as_uuid=True),
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "actor_id",
        PGUUID(as_uuid=True),
        ForeignKey("actors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

movies_languages = Table(
    "movies_languages",
    Base.metadata,
    Column(
        "movie_id",
        PGUUID(as_uuid=True),
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "language_id",
        PGUUID(as_uuid=True),
        ForeignKey("languages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=movies_genres,
        back_populates="genres",
    )

    __table_args__ = (
        Index("uq_genres_name_lower", func.lower(name), unique=True),
    )


class ActorModel(Base):
    __tablename__ = "actors"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=movies_actors,
        back_populates="actors",
    )

    __table_args__ = (
        Index("ix_actors_name_lower", func.lower(name)),
    )


class CountryModel(Base):
    __tablename__ = "countries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    movies: Mapped[list["MovieModel"]] = relationship(
        back_populates="country",
    )

    __table_args__ = (
        Index("uq_countries_code_lower", func.lower(code), unique=True),
    )

class LanguageModel(Base):
    __tablename__ = "languages"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    movies: Mapped[list["MovieModel"]] = relationship(
        secondary=movies_languages,
        back_populates="languages",
    )

    __table_args__ = (
        Index("uq_languages_name_lower", func.lower(name), unique=True),
    )


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MovieStatusEnum] = mapped_column(
        Enum(
            MovieStatusEnum,
            name="movie_status_enum",
            native_enum=True,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    price: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    country_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    country: Mapped["CountryModel"] = relationship(back_populates="movies")
    genres: Mapped[list["GenreModel"]] = relationship(
        secondary=movies_genres,
        back_populates="movies",
    )
    actors: Mapped[list["ActorModel"]] = relationship(
        secondary=movies_actors,
        back_populates="movies",
    )
    languages: Mapped[list["LanguageModel"]] = relationship(
        secondary=movies_languages,
        back_populates="movies",
    )
    cart_items: Mapped[list["CartItemModel"]] = relationship(
        back_populates="movie",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "uq_movies_name_lower_date",
            func.lower(name),
            date,
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        CheckConstraint("budget >= 0", name="budget_non_negative"),
        CheckConstraint("revenue >= 0", name="revenue_non_negative"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )

