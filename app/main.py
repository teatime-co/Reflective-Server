from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app.api import tags, auth, users, encryption, sync, health, metrics
from app.database import engine
from app.models.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Reflective API",
    description="API for the Reflective journaling app with RAG capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(encryption.router, prefix="/api")
app.include_router(sync.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Reflective API"}

 