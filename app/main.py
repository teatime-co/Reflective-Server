from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import logs, tags
from app.database import engine
from app.models.models import Base
import os

# Create database tables
Base.metadata.create_all(bind=engine)

# Ensure Weaviate data directory exists
weaviate_data_dir = os.path.join(os.getcwd(), "weaviate-data")
os.makedirs(weaviate_data_dir, exist_ok=True)

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
app.include_router(logs.router, prefix="/api")
app.include_router(tags.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Reflective API"}

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup Weaviate embedded instance on shutdown"""
    from app.api.logs import rag_service
    if hasattr(rag_service.client, '_embedded_db'):
        rag_service.client._embedded_db.stop() 