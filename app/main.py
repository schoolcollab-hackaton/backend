from fastapi import (
    FastAPI,
)
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from app.utils import get_allowed_origins
from app.models.models import *
from app.routers import auth, contact, groupe, publication, dashboard, profile, demande_soutien, recommendation, request, mentor
from app.ai.chatbot.router import router as chatbot_router

from data.mock import (
    populate_mock_data
)

from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os

app = FastAPI(
    title="SchoolCollab API",
    description="Social collaboration platform for Estiam students",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://data/schoolcollab.db")

MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/media", StaticFiles(directory="media"), name="media")

# Database initialization
register_tortoise(
    app,
    db_url=DATABASE_URL,
    modules={"models": ["app.models.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(contact.router)
app.include_router(chatbot_router)
app.include_router(groupe.router)
app.include_router(dashboard.router)
app.include_router(publication.router)
app.include_router(demande_soutien.router)
app.include_router(recommendation.router)
app.include_router(request.router)
app.include_router(mentor.router)

@app.on_event("startup")
async def startup_event():
    """Initialize database with mock data if empty"""
    try:
        # Check if database has any users
        user_count = await Utilisateur.all().count()
        print(f"Found {user_count} users in database")
        
        if user_count == 0:
            print("Database is empty, populating with mock data...")
            await populate_mock_data()
        else:
            print("Database already has users, skipping mock data population")
            
    except Exception as e:
        print(f"Error during startup: {e}")
