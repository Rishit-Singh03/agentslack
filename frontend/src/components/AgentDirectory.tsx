import { ArrowUpRight, Bot, Plus } from 'lucide-react'
import type { Agent } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export function AgentDirectory({
  agents,
  profile,
  hire,
}: {
  agents: Agent[]
  profile: (a: Agent) => void
  hire: () => void
}) {
  return (
    <>
      <header className="view-header">
        <div className="header-title">
          <Bot size={25} />
          <div>
            <h2>Your people. Powered by possibility.</h2>
            <p>{agents.length} specialists, one shared ambition.</p>
          </div>
        </div>
        <button className="primary-button" onClick={hire}>
          <Plus size={16} />
          Hire agent
        </button>
      </header>
      <div className="directory">
        <span className="eyebrow">SMALL TEAM. BIG IDEAS.</span>
        <h1>A specialist for every spark.</h1>
        <p className="directory-description">
          Meet the minds behind the work. Pick a teammate to see what makes them tick.
        </p>
        <div className="agent-grid">
          {agents.map((a) => (
            <button className="agent-card" key={a.id} onClick={() => profile(a)}>
              <div className="agent-card-top">
                <AgentAvatar agent={a} size={54} />
                <span className="level-pill">✧ Level {a.level}</span>
                <ArrowUpRight size={17} />
              </div>
              <h2>{a.name}</h2>
              <p>{a.title}</p>
              <span className={`role-badge role-${a.role}`}>{a.role}</span>
              <div className="skill-list">
                {a.skills.map((s) => (
                  <span key={s}>{s}</span>
                ))}
              </div>
              <div className="agent-card-footer">
                <span className={`inline-dot ${a.status}`} />
                {a.status}
                <span>{a.xp} XP</span>
              </div>
            </button>
          ))}
          <button className="agent-card hire-card" onClick={hire}>
            <span>
              <Plus size={25} />
            </span>
            <h2>Room for one more.</h2>
            <p>Your next great teammate is an idea away.</p>
            <strong>
              Hire an agent <ArrowUpRight size={14} />
            </strong>
          </button>
        </div>
      </div>
    </>
  )
}
