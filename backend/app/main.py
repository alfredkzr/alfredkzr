from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import bookings, bot, settings, targets, ws
from app.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Omakase Booking Bot",
    description="Automated booking bot for Omakase.in restaurants",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(targets.router, prefix="/api/targets", tags=["targets"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(bot.router, prefix="/api/bot", tags=["bot"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
