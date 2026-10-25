import { useEffect, useState } from 'react'
import { Brain, MessageSquare, X, Sparkles } from 'lucide-react'
import { api } from '../api/client'
import type { Agent, MemoryEntry, Task } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export function AgentProfile({
  agent,
  tasks,
  close,
  dm,
}: {
  agent: Agent
  tasks: Task[]
  close: () => void
  dm: (a: Agent) => void
}) {
  const [memory, setMemory] = useState<MemoryEntry[]>([])
  const [memoryError, setMemoryError] = useState(false)
  useEffect(() => {
    let alive = true
    setMemory([])
    setMemoryError(false)
    api
      .memory(agent.id)
      .then((m) => {
        if (alive) setMemory(m)
      })
      .catch(() => {
        if (alive) setMemoryError(true)
      })
    return () => {
      alive = false
    }
  }, [agent.id])
  return (
    <aside className="profile">
      <div className="profile-heading">
        Agent profile
        <button className="icon-button" onClick={close} aria-label="Close profile">
          <X size={18} />
        </button>
      </div>
      <div className="profile-scroll">
        <div className="profile-identity">
          <AgentAvatar agent={agent} size={80} />
          <h2>
            {agent.name}
            <Sparkles size={16} />
          </h2>
          <p>{agent.title}</p>
          <span className="profile-status">
            <span className={`inline-dot ${agent.status}`} />
            {agent.status === 'busy' ? 'Thinking' : agent.status}
          </span>
          <button className="primary-button" onClick={() => dm(agent)}>
            <MessageSquare size={15} />
            Message {agent.name}
          </button>
        </div>
        <section className="profile-section">
          <h3>ABOUT</h3>
          <p>{agent.bio || 'A new teammate, ready to help with your next big idea.'}</p>
          <span className={`role-badge role-${agent.role}`}>{agent.role}</span>
          <span className="runtime-tag">Stub runtime</span>
        </section>
        <section className="profile-section">
          <h3>GROWING WITH YOU</h3>
          <div className="level-row">
            <span className="level-icon">✧</span>
            <div>
              <strong>Level {agent.level}</strong>
              <small>{agent.xp} lifetime XP</small>
            </div>
            <span>{agent.xp % 100}/100 XP</span>
          </div>
          <div className="xp-track">
            <div style={{ width: `${agent.xp % 100}%` }} />
          </div>
          <p className="muted-small">
            {100 - (agent.xp % 100)} XP to level {agent.level + 1}. Great work adds up.
          </p>
        </section>
        <section className="profile-section">
          <h3>SUPERPOWERS</h3>
          <div className="skill-list">
            {agent.skills.length ? (
              agent.skills.map((s) => <span key={s}>{s}</span>)
            ) : (
              <p>Skills will appear here.</p>
            )}
          </div>
        </section>
        <section className="profile-section">
          <h3>
            CURRENT TASKS{' '}
            <span>
              {tasks.filter((t) => t.assignee_agent_id === agent.id && t.status !== 'done').length}
            </span>
          </h3>
          {tasks
            .filter((t) => t.assignee_agent_id === agent.id && t.status !== 'done')
            .map((t) => (
              <div className="profile-task" key={t.id}>
                <span className="tiny-dot" />
                {t.title}
                <small>{t.status.replace('_', ' ')}</small>
              </div>
            ))}
          {!tasks.some((t) => t.assignee_agent_id === agent.id && t.status !== 'done') && (
            <p className="muted-small">All clear. Ready for a new challenge.</p>
          )}
        </section>
        <section className="profile-section">
          <h3>
            <Brain size={14} /> MEMORY
          </h3>
          {memory.length ? (
            memory.map((m) => <p key={m.id}>{m.content}</p>)
          ) : (
            <div className="memory-empty">
              <Brain size={22} />
              <strong>{memoryError ? 'Memory unavailable' : 'A fresh mind, for now'}</strong>
              <p>
                {memoryError
                  ? 'Try opening this profile again.'
                  : 'Long-term memories and learnings are coming in a future phase.'}
              </p>
            </div>
          )}
        </section>
      </div>
    </aside>
  )
}
