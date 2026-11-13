from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, ai, books, chapters, illustrations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(ai.router)
api_router.include_router(books.router)
api_router.include_router(chapters.router)
api_router.include_router(illustrations.router)
