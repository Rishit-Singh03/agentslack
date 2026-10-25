import { Hash, PanelRight, Users } from 'lucide-react'
import type { Agent, Channel, Message } from '../api/types'
import { AgentAvatar } from './AgentAvatar'
import { Composer } from './Composer'
import { MessageList } from './MessageList'

export function ChannelView(p: {
  channel: Channel
  agents: Agent[]
  messages: Message[]
  loading: boolean
  more: boolean
  loadMore: () => void
  send: (body: string) => Promise<void>
  profile: (a: Agent) => void
}) {
  const members = p.agents.filter(
    (a) => p.channel.member_ids?.includes(a.id) || a.id === p.channel.dm_agent_id,
  )
  const busy = p.agents.filter(
    (a) =>
      a.status === 'busy' &&
      (members.some((m) => m.id === a.id) || p.messages.some((m) => m.author_id === a.id)),
  )
  return (
    <>
      <header className="view-header">
        <div className="header-title">
          {p.channel.is_dm ? <Users size={23} /> : <Hash size={25} />}
          <div>
            <h2>
              {p.channel.name}
              <span className="header-tag">{p.channel.is_dm ? 'DIRECT MESSAGE' : 'CHANNEL'}</span>
            </h2>
            <p>{p.channel.topic}</p>
          </div>
        </div>
        <div className="member-stack">
          {members.slice(0, 4).map((a) => (
            <button
              key={a.id}
              className="avatar-button"
              onClick={() => p.profile(a)}
              title={a.name}
            >
              <AgentAvatar agent={a} size={27} />
            </button>
          ))}
          <span>{members.length}</span>
        </div>
        <button
          className="icon-button"
          aria-label="Open agent profile"
          onClick={() => members[0] && p.profile(members[0])}
          disabled={!members.length}
        >
          <PanelRight size={19} />
        </button>
      </header>
      <div className="channel-note">
        <span className="tiny-dot" /> A space for good ideas and great teamwork.
        <span>Make yourself at home.</span>
      </div>
      {p.loading ? (
        <div className="loading-state">Loading the conversation…</div>
      ) : (
        <MessageList
          messages={p.messages}
          agents={p.agents}
          channel={p.channel}
          profile={p.profile}
          more={p.more}
          loadMore={p.loadMore}
        />
      )}
      <div className="typing" aria-live="polite">
        {busy.length > 0 && (
          <>
            <span className="typing-dots">•••</span> {busy.map((a) => a.name).join(', ')}{' '}
            {busy.length > 1 ? 'are' : 'is'} thinking…
          </>
        )}
      </div>
      <Composer
        key={p.channel.id}
        agents={p.agents}
        name={p.channel.is_dm ? p.channel.name : `#${p.channel.name}`}
        send={p.send}
      />
    </>
  )
}
