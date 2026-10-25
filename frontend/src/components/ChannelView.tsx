import type { Agent, Channel, Department, Message, UserProfile } from '../api/types'
import { Composer } from './Composer'
import { MessageList } from './MessageList'

export function ChannelView(p: {
  channel: Channel
  agents: Agent[]
  departments: Department[]
  messages: Message[]
  loading: boolean
  more: boolean
  loadMore: () => void
  send: (body: string) => Promise<void>
  profile: (agent: Agent) => void
  info: () => void
  me: UserProfile
  flashes: number[]
  onMode: (mode: 'NORMAL' | 'INSERT') => void
}) {
  const members = p.agents.filter(
    (agent) => p.channel.member_ids?.includes(agent.id) || agent.id === p.channel.dm_agent_id,
  )
  const busy = members.filter((agent) => agent.status === 'busy')
  return (
    <>
      <header className="view-header">
        <h1>
          {p.channel.is_dm ? '@' : '#'}
          {p.channel.name.toLowerCase()}
        </h1>
        <span className="topic">{p.channel.topic || 'No topic set'}</span>
        <span className="member-count">{members.length} members</span>
        <button onClick={p.info} aria-label="Channel info">
          [i]
        </button>
      </header>
      {p.loading ? (
        <p className="empty-state">Loading messages...</p>
      ) : (
        <MessageList
          messages={p.messages}
          agents={p.agents}
          departments={p.departments}
          channel={p.channel}
          profile={p.profile}
          more={p.more}
          loadMore={p.loadMore}
          me={p.me}
          flashes={p.flashes}
        />
      )}
      <div className="typing" aria-live="polite">
        {busy.length > 0 && (
          <span>
            {busy.map((agent) => agent.handle).join(', ')}{' '}
            <span className="typing-dots">working...</span>
          </span>
        )}
      </div>
      <Composer
        departments={p.departments}
        key={p.channel.id}
        agents={p.agents}
        name={p.channel.is_dm ? p.channel.name : `#${p.channel.name}`}
        send={p.send}
        onMode={p.onMode}
      />
    </>
  )
}
