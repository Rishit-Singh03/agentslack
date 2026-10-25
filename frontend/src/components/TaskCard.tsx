import type { Agent, Task, TaskStatus } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export const stages: { id: TaskStatus; label: string; color: string }[] = [
  { id: 'todo', label: 'To do', color: '#92909d' },
  { id: 'in_progress', label: 'In progress', color: '#a78bfa' },
  { id: 'review', label: 'In review', color: '#fbbf24' },
  { id: 'done', label: 'Done', color: '#34d399' },
]
export function TaskCard({
  task,
  agent,
  move,
  profile,
}: {
  task: Task
  agent?: Agent
  move: (id: number, status: TaskStatus) => void
  profile: (a: Agent) => void
}) {
  return (
    <article className="task-card">
      <div className="task-topline">
        <span className={`priority ${task.priority}`}>
          {task.priority === 'med' ? 'Medium' : task.priority} priority
        </span>
        <span>#{String(task.id).padStart(3, '0')}</span>
      </div>
      <h3>{task.title}</h3>
      <p>{task.description}</p>
      <div className="task-assignee">
        {agent && (
          <button onClick={() => profile(agent)}>
            <AgentAvatar agent={agent} size={24} />
            {agent.name}
          </button>
        )}
        <span className="xp-reward">✧ {task.xp_reward} XP</span>
      </div>
      <select
        aria-label={`Status of ${task.title}`}
        value={task.status}
        onChange={(e) => move(task.id, e.target.value as TaskStatus)}
      >
        {stages.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>
    </article>
  )
}
