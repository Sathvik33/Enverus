from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.routes_documents import router as documents_router
from app.api.routes_chat import router as chat_router
from app.api.routes_auth import router as auth_router
from app.api.routes_history import router as history_router
from app.api.routes_sessions import router as sessions_router
from app.db.database import init_db
from app.core.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("main")
    logger.info("starting_application")
    await init_db()
    logger.info("database_initialized")
    yield
    logger.info("shutting_down")


app = FastAPI(
    title="Multimodal RAG — Agent-as-a-Judge",
    description="Evidence-grounded multimodal RAG system for research papers",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(sessions_router)

image_dir = Path("data/images")
if image_dir.exists():
    app.mount("/images", StaticFiles(directory=str(image_dir)), name="images")


@app.get("/health")
async def health():
    return {"status": "ok"}
