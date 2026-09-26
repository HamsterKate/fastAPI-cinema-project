from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.core.config import settings
from app.profiles.router import router as profiles_router


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(
    accounts_router,
    prefix=settings.api_prefix,
)

app.include_router(
    profiles_router,
    prefix=settings.api_prefix,
)