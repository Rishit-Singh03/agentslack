import type { Agent, Department, Task, TaskStatus } from '../api/types'
import { stages, TaskCard } from './TaskCard'

export function TaskBoard({
  tasks,
  agents,
  departments,
  create,
  move,
  profile,
}: {
  tasks: Task[]
  agents: Agent[]
  departments: Department[]
  create: () => void
  move: (id: number, status: TaskStatus) => void
  profile: (agent: Agent) => void
}) {
  return (
    <>
      <header className="view-header">
        <h1>tasks</h1>
        <span className="topic">
          {tasks.length} total / {tasks.filter((task) => task.status === 'done').length} completed
        </span>
        <button className="header-action" onClick={create}>
          [n] new task
        </button>
      </header>
      <div className="view-note">
        Focus a task and press h / l to change status, or use its dropdown.
      </div>
      <div className="kanban">
        {stages.map((stage) => (
          <section className="kanban-column" key={stage.id}>
            <h2>
              {stage.label} ({tasks.filter((task) => task.status === stage.id).length})
            </h2>
            {tasks
              .filter((task) => task.status === stage.id)
              .map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  departments={departments}
                  agent={agents.find((agent) => agent.id === task.assignee_agent_id)}
                  move={move}
                  profile={profile}
                />
              ))}
            {!tasks.some((task) => task.status === stage.id) && (
              <p className="empty-state">No tasks. Press n to create one.</p>
            )}
          </section>
        ))}
      </div>
    </>
  )
}
