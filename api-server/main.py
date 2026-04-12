from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from app.native import NativeVideoPokerClient
from app.routers.coach import router as coach_router
from app.routers.evaluate import router as evaluate_router
from app.routers.strategy import router as strategy_router


def create_app(
    *,
    native_client: NativeVideoPokerClient | object | None = None,
    load_native_on_startup: bool = True,
) -> FastAPI:
    lib_path = os.path.join(os.path.dirname(__file__), "libvideopoker.so")
    resolved_native_client = native_client or NativeVideoPokerClient(lib_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.native_client = resolved_native_client
        if load_native_on_startup and hasattr(app.state.native_client, "load"):
            app.state.native_client.load()
        yield

    app = FastAPI(title="Video Poker API", lifespan=lifespan)

    @app.get("/")
    async def root():
        return {
            "service": "Video Poker API",
            "status": "ok",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "endpoints": [
                "/v1/video-poker/strategy",
                "/v1/poker/evaluate",
                "/v1/coach/compare",
                "/v1/coach/session-summary",
                "/v1/coach/drill-recommendation",
            ],
        }
    app.include_router(strategy_router)
    app.include_router(evaluate_router)
    app.include_router(coach_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
