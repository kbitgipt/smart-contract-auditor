from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="AuditSmart API",
    description="Smart Contract Auditing Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - support both local and docker
allowed_origins = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://frontend:3000",   # Docker frontend service
]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


from app.api import auth, upload, analysis, projects

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])

@app.get("/")
async def root():
    return {
        "message": "AuditSmart API is running!",
        "version": "1.0.0",
        "environment": os.getenv("DEBUG", "production")
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Enable for development
        log_level="debug" if os.getenv("DEBUG") == "True" else "info"
    )