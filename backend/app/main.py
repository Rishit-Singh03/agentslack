from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .db import create_all, engine
from .realtime import manager
from .routers import agents, channels, messages, tasks
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    with Session(engine) as session:
        seed(session)
    yield


app = FastAPI(title="agentslack", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (agents.router, channels.router, messages.router, tasks.router):
    app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok", "workspace": "Acme Agents"}


@app.websocket("/ws")
async def websocket(socket: WebSocket):
    await manager.connect(socket)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(socket)
