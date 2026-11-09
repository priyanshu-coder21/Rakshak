from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from routes import distress, rescue, dispatch, telegram

# Load environment variables from .env file for local development
load_dotenv()

app = FastAPI(
    title="RAKSHAK API",
    description="Standalone AI-powered disaster response and rescue coordination API",
    version="1.0.0"
)

# Read allowed frontend URLs from environment variables (comma-separated)
# Defaults to local development ports (VS Code Live Server / HTTP Server) if not set
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000"
)
allowed_origins = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Automatically allows Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root & Health Check Endpoints for Render
@app.get("/")
def root():
    return {"status": "online", "service": "RAKSHAK Standalone API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include API Routers ONLY (No HTML page routers)
app.include_router(distress.router)
app.include_router(rescue.router)
app.include_router(dispatch.router)
app.include_router(telegram.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )