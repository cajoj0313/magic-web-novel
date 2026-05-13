"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(level=settings.log_level)
    yield
    # Shutdown


app = FastAPI(title="WebNovel Web App", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# Register all API routers
from app.api.chapter_router import router as chapter_router  # noqa: E402
from app.api.learn_router import router as learn_router  # noqa: E402
from app.api.llm_config_router import router as llm_config_router  # noqa: E402
from app.api.plan_router import router as plan_router  # noqa: E402
from app.api.project_router import router as project_router  # noqa: E402
from app.api.query_router import router as query_router  # noqa: E402
from app.api.review_router import router as review_router  # noqa: E402
from app.api.setting_router import router as setting_router  # noqa: E402
from app.api.sse_router import router as sse_router  # noqa: E402
from app.api.task_router import router as task_router  # noqa: E402

app.include_router(chapter_router)
app.include_router(learn_router)
app.include_router(llm_config_router)
app.include_router(plan_router)
app.include_router(project_router)
app.include_router(query_router)
app.include_router(review_router)
app.include_router(setting_router)
app.include_router(sse_router)
app.include_router(task_router)
