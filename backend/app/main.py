from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .db import create_all, engine, get_session
from .models import Organization
from .realtime import manager
from .routers import agents, channels, departments, messages, settings, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    with Session(engine) as session:
        settings.ensure_settings(session)
    yield


app = FastAPI(title="agentslack", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (
    agents.router,
    channels.router,
    messages.router,
    tasks.router,
    settings.router,
    departments.router,
):
    app.include_router(router)


@app.get("/api/health")
def health(session: Session = Depends(get_session)):
    org = session.exec(select(Organization)).one()
    return {"status": "ok", "workspace": org.name}


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
