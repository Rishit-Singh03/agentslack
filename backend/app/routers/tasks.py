from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, Channel, Message, Task, now
from ..realtime import manager
from ..schemas import TaskCreate, TaskPatch
from .agents import require

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def tasks(session: Session = Depends(get_session)):
    return session.exec(select(Task).order_by(Task.id)).all()


@router.post("", response_model=Task, status_code=201)
async def create_task(data: TaskCreate, session: Session = Depends(get_session)):
    require(session, Agent, data.assignee_agent_id)
    if data.channel_id is not None:
        require(session, Channel, data.channel_id)
    task = Task(**data.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    await manager.broadcast("task.updated", task)
    return task


@router.patch("/{task_id}", response_model=Task)
async def patch_task(task_id: int, data: TaskPatch, session: Session = Depends(get_session)):
    task = require(session, Task, task_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "assignee_agent_id" in changes:
        require(session, Agent, changes["assignee_agent_id"])
    previous = task.status
    task.sqlmodel_update(changes)
    task.updated_at = now()
    agent = None
    if task.status == "done" and not task.xp_awarded:
        agent = require(session, Agent, task.assignee_agent_id)
        agent.xp += task.xp_reward
        agent.level = 1 + agent.xp // 100
        task.xp_awarded = True
        session.add(agent)
    message = None
    if previous != task.status and task.channel_id:
        message = Message(
            channel_id=task.channel_id,
            author_type="system",
            body=f'Task "{task.title}" moved to {task.status.replace("_", " ")}.',
        )
        session.add(message)
    session.add(task)
    session.commit()
    session.refresh(task)
    await manager.broadcast("task.updated", task)
    if agent:
        session.refresh(agent)
        await manager.broadcast("agent.updated", agent)
    if message:
        session.refresh(message)
        await manager.broadcast("message.created", message)
    return task
