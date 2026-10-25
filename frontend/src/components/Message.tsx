import ReactMarkdown from 'react-markdown'
import { Sparkles } from 'lucide-react'
import type { Agent, Message as MessageType } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export function Message({
  message,
  agent,
  grouped,
  profile,
}: {
  message: MessageType
  agent?: Agent
  grouped: boolean
  profile: (a: Agent) => void
}) {
  const time = new Date(message.created_at).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
  if (message.author_type === 'system')
    return (
      <div className="system-message">
        <Sparkles size={13} />
        <span>{message.body}</span>
      </div>
    )
  return (
    <article className={`message ${grouped ? 'grouped' : ''}`}>
      {!grouped &&
        (agent ? (
          <button
            className="avatar-button"
            onClick={() => profile(agent)}
            aria-label={`View ${agent.name}'s profile`}
          >
            <AgentAvatar agent={agent} />
          </button>
        ) : (
          <span className="avatar human-avatar">Y</span>
        ))}
      {grouped && <span className="compact-time">{time}</span>}
      <div className="message-content">
        {!grouped && (
          <div className="message-meta">
            <button onClick={() => agent && profile(agent)} className="author">
              {agent?.name ?? 'You'}
            </button>
            {agent && <span className={`role-badge role-${agent.role}`}>{agent.role}</span>}
            <time dateTime={message.created_at}>{time}</time>
          </div>
        )}
        <div className="markdown">
          <ReactMarkdown>{message.body}</ReactMarkdown>
        </div>
      </div>
    </article>
  )
}
