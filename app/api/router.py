from fastapi import APIRouter
from app.api.routes.user_query_route import router as user_query_router
from app.api.routes.threads_route import router as threads_router
api_router = APIRouter()
api_router.include_router(
    user_query_router,
    prefix="/user-query",
    tags=["User Query"],
)
api_router.include_router(
    threads_router,
    prefix="/threads",
    tags=["Threads"],
)