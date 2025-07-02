from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form, Response, Request, Depends
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from app.utils import get_allowed_origins
from app.models.models import *
from app.routers import auth
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import logging

app = FastAPI(title="SchoolCollab API", description="Social collaboration platform for Estiam students")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://data/schoolcollab.db")



MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/media", StaticFiles(directory="media"), name="media")

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/ping")
async def ping():
    logger.info("Ping endpoint hit.")
    return {"message": "pong from FastAPI backend!"}

app.include_router(auth.router)