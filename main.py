from fastapi import FastAPI

from app.accounts.router import router as accounts_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(
    accounts_router,
    prefix=settings.api_prefix,
)