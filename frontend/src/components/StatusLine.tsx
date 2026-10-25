import type { Agent, Org, Task } from '../api/types'

export function StatusLine({
  mode,
  org,
  view,
  agents,
  tasks,
  connected,
}: {
  mode: string
  org: Org
  view: string
  agents: Agent[]
  tasks: Task[]
  connected: boolean
}) {
  return (
    <footer className="status-line">
      <strong>{mode}</strong>
      <span>{org.slug}</span>
      <span>{view}</span>
      <span>
        {agents.length} agents · {agents.filter((agent) => agent.status === 'online').length} online
      </span>
      <span>{tasks.filter((task) => task.status === 'in_progress').length} tasks in progress</span>
      <span className={connected ? 'ok' : 'warn'}>
        {connected ? '● connected' : '○ disconnected — retrying in 3s'}
      </span>
    </footer>
  )
}
