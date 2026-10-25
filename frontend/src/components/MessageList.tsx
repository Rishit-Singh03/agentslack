import { useEffect, useRef } from 'react'
import type { Agent, Channel, Message as MessageType } from '../api/types'
import { Message } from './Message'

export function MessageList({
  messages,
  agents,
  channel,
  profile,
  more,
  loadMore,
}: {
  messages: MessageType[]
  agents: Agent[]
  channel: Channel
  profile: (a: Agent) => void
  more: boolean
  loadMore: () => void
}) {
  const end = useRef<HTMLDivElement>(null)
  const previousLast = useRef<number>()
  useEffect(() => {
    const last = messages.at(-1)?.id
    if (last !== previousLast.current)
      end.current?.scrollIntoView({ behavior: previousLast.current ? 'smooth' : 'auto' })
    previousLast.current = last
  }, [messages])
  const day = (value: string) =>
    new Date(value).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
  return (
    <div className="message-list" role="log" aria-label="Conversation">
      {more ? (
        <button className="load-more" onClick={loadMore}>
          Load older messages
        </button>
      ) : (
        <div className="channel-welcome">
          <div className="channel-welcome-icon">{channel.is_dm ? '↗' : '#'}</div>
          <h1>{channel.is_dm ? channel.name : `Welcome to #${channel.name}`}</h1>
          <p>
            {channel.is_dm
              ? `This is the beginning of your conversation with ${channel.name}. Say hello or share something to work on.`
              : 'A shared space for your team to think, build, and make things happen.'}
          </p>
        </div>
      )}
      {messages.map((m, i) => {
        const previous = messages[i - 1]
        const newDay = !previous || day(previous.created_at) !== day(m.created_at)
        const grouped =
          !newDay &&
          previous.author_type === m.author_type &&
          previous.author_id === m.author_id &&
          new Date(m.created_at).getTime() - new Date(previous.created_at).getTime() < 300000
        return (
          <div key={m.id}>
            {newDay && (
              <div className="day-divider">
                <span>{day(m.created_at)}</span>
              </div>
            )}
            <Message
              message={m}
              agent={agents.find((a) => a.id === m.author_id)}
              grouped={grouped}
              profile={profile}
            />
          </div>
        )
      })}
      <div ref={end} />
    </div>
  )
}
