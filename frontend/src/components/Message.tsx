import { DepartmentTag, departmentStyle } from './DepartmentTag'
import ReactMarkdown from 'react-markdown'
import type { Agent, Department, Message as MessageType, UserProfile } from '../api/types'
import { clockTime } from '../utils'

export function Message({
  message,
  agent,
  grouped,
  profile,
  me,
  flashing,
  department,
}: {
  message: MessageType
  agent?: Agent
  department?: Department
  grouped: boolean
  profile: (agent: Agent) => void
  me: UserProfile
  flashing: boolean
}) {
  const handle =
    message.author_type === 'human'
      ? me.handle
      : (agent?.handle ?? (message.author_type === 'system' ? '--' : '@dismissed'))
  return (
    <article className={`message ${message.author_type === 'system' ? 'system-message' : ''}`}>
      <time dateTime={message.created_at}>{clockTime(message.created_at)}</time>
      <div className="message-author">
        {!grouped && (
          <>
            <button
              className={`handle department-handle ${flashing ? 'level-flash' : ''}`}
              style={departmentStyle(department)}
              onClick={() => agent && profile(agent)}
            >
              {handle}
            </button>
            {agent && (
              <small>
                <DepartmentTag department={department} /> lvl {agent.level}
              </small>
            )}
          </>
        )}
      </div>
      <div className="message-body">
        <div className="markdown">
          <ReactMarkdown>{message.body}</ReactMarkdown>
        </div>
        {message.is_streaming && (
          <span className="stream-caret" aria-label="Streaming reply">
            ▍
          </span>
        )}
        {message.author_type === 'agent' && message.model_id && message.usage && (
          <small className="message-meta dim">
            {message.model_id} · {message.usage.totalTokens.toLocaleString()} tokens · $
            {Number(message.cost_usd ?? 0).toFixed(6)}
            {message.usage.price_basis === 'list' && ' list price · via relay'}
          </small>
        )}
        {message.author_type === 'agent' &&
          message.model_id &&
          !message.usage &&
          !message.is_streaming && (
            <small className="message-meta dim">
              {message.model_id} · usage unavailable · reservation held
            </small>
          )}
      </div>
    </article>
  )
}
