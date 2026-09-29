from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import comments, issues, labels, members, projects, stories
from app.config import settings
from app.database import Base, engine
import app.models  # noqa: F401  # register ORM tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(projects.router, prefix="/api")
app.include_router(stories.router, prefix="/api")
app.include_router(issues.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(labels.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
