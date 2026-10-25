import { departmentStyle } from './DepartmentTag'
import type { Agent, Department, Task, TaskStatus } from '../api/types'

export const stages: { id: TaskStatus; label: string }[] = [
  { id: 'todo', label: 'TODO' },
  { id: 'in_progress', label: 'IN PROGRESS' },
  { id: 'review', label: 'REVIEW' },
  { id: 'done', label: 'DONE' },
]
export function TaskCard({
  task,
  departments,
  agent,
  move,
  profile,
}: {
  task: Task
  departments: Department[]
  agent?: Agent
  move: (id: number, status: TaskStatus) => void
  profile: (agent: Agent) => void
}) {
  return (
    <article
      className="task-card"
      tabIndex={0}
      aria-label={`Task ${task.title}`}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget || !['h', 'l'].includes(event.key)) return
        event.preventDefault()
        const index = stages.findIndex((stage) => stage.id === task.status)
        move(
          task.id,
          stages[Math.max(0, Math.min(stages.length - 1, index + (event.key === 'l' ? 1 : -1)))].id,
        )
      }}
    >
      <div className="task-meta">
        <span>#{String(task.id).padStart(3, '0')}</span>
        <span>[{task.priority}]</span>
      </div>
      <h3>{task.title}</h3>
      <p>{task.description}</p>
      <div className="task-assignee">
        <button
          className="handle department-handle"
          style={departmentStyle(
            departments.find((department) => department.id === agent?.department_id),
          )}
          onClick={() => agent && profile(agent)}
        >
          {agent?.handle ?? 'unassigned'}
        </button>
        <span>+{task.xp_reward}xp</span>
      </div>
      <select
        aria-label={`Status of ${task.title}`}
        value={task.status}
        onChange={(event) => move(task.id, event.target.value as TaskStatus)}
      >
        {stages.map((stage) => (
          <option key={stage.id} value={stage.id}>
            {stage.label}
          </option>
        ))}
      </select>
    </article>
  )
}
