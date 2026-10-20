from contextlib import asynccontextmanager

from app.api.router import api_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.graph.workflow import build_graph
from app.core.config import BASE_DIR

FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_path = BASE_DIR / "checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as checkpointer:
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")