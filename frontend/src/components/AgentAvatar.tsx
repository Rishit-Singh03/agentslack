import type { Agent } from '../api/types'

export function AgentAvatar({ agent, size = 36 }: { agent: Agent; size?: number }) {
  return (
    <span
      className="avatar"
      style={{
        width: size,
        height: size,
        background: `${agent.avatar_color}25`,
        color: agent.avatar_color,
        fontSize: size * 0.4,
      }}
      aria-label={`${agent.name}, ${agent.status}`}
    >
      {agent.name.slice(0, 1)}
      <span className={`status-dot ${agent.status}`} />
    </span>
  )
}
