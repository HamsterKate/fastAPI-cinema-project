from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.cart.router import router as cart_router
from app.movies.router import router as movies_router
from app.core.config import settings
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(
    accounts_router,
    prefix=settings.api_prefix,
)

app.include_router(
    movies_router,
    prefix=settings.api_prefix,
)

app.include_router(
    cart_router,
    prefix=settings.api_prefix,
)

app.include_router(
    orders_router,
    prefix=settings.api_prefix,
)

app.include_router(
    payments_router,
    prefix=settings.api_prefix
)