import { Plus, ListTodo } from 'lucide-react'
import type { Agent, Task, TaskStatus } from '../api/types'
import { stages, TaskCard } from './TaskCard'

export function TaskBoard({
  tasks,
  agents,
  create,
  move,
  profile,
}: {
  tasks: Task[]
  agents: Agent[]
  create: () => void
  move: (id: number, status: TaskStatus) => void
  profile: (a: Agent) => void
}) {
  return (
    <>
      <header className="view-header">
        <div className="header-title">
          <ListTodo size={24} />
          <div>
            <h2>Team tasks</h2>
            <p>From a little idea to a job well done.</p>
          </div>
        </div>
        <button className="primary-button" onClick={create}>
          <Plus size={16} />
          Create task
        </button>
      </header>
      <div className="board-intro">
        <span className="eyebrow">BETTER TOGETHER</span>
        <h1>Good work, in motion.</h1>
        <p>Give your agents a direction. Watch your ideas take shape.</p>
        <div className="board-stats">
          <span>
            <strong>{tasks.length}</strong> total tasks
          </span>
          <span>
            <strong>{tasks.filter((t) => t.status === 'done').length}</strong> completed
          </span>
          <span>✧ Every finished task helps your team grow</span>
        </div>
      </div>
      <div className="kanban">
        {stages.map((s) => (
          <section className="kanban-column" key={s.id}>
            <h3>
              <span style={{ background: s.color }} className="stage-dot" />
              {s.label}
              <span className="count">{tasks.filter((t) => t.status === s.id).length}</span>
              <button className="icon-button" onClick={create} aria-label="Create a task">
                <Plus size={15} />
              </button>
            </h3>
            {tasks
              .filter((t) => t.status === s.id)
              .map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  agent={agents.find((a) => a.id === t.assignee_agent_id)}
                  move={move}
                  profile={profile}
                />
              ))}
            {!tasks.some((t) => t.status === s.id) && (
              <div className="empty-column">Room for what's next.</div>
            )}
          </section>
        ))}
      </div>
    </>
  )
}
