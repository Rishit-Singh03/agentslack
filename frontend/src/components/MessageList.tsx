import { useEffect, useRef } from 'react'
import type { Agent, Channel, Department, Message as MessageType, UserProfile } from '../api/types'
import { utcDate } from '../utils'
import { Message } from './Message'

export function MessageList({
  messages,
  agents,
  channel,
  profile,
  more,
  loadMore,
  me,
  flashes,
  departments,
}: {
  messages: MessageType[]
  agents: Agent[]
  departments: Department[]
  channel: Channel
  profile: (agent: Agent) => void
  more: boolean
  loadMore: () => void
  me: UserProfile
  flashes: number[]
}) {
  const end = useRef<HTMLDivElement>(null)
  const previous = useRef<number>()
  const last = messages.at(-1)
  useEffect(() => {
    if (last?.id !== previous.current || last?.is_streaming)
      end.current?.scrollIntoView({ block: 'end' })
    previous.current = last?.id
  }, [last?.id, last?.body, last?.is_streaming])
  const day = (value: string) =>
    utcDate(value).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short' })
  return (
    <div className="message-list" role="log" aria-label="Conversation">
      {more && (
        <button className="load-more" onClick={loadMore}>
          [load earlier messages]
        </button>
      )}
      {!messages.length && (
        <p className="empty-state">
          No messages in {channel.is_dm ? channel.name : `#${channel.name}`}. Type below to start a
          conversation.
        </p>
      )}
      {messages.map((message, index) => {
        const prior = messages[index - 1]
        const newDay = !prior || day(prior.created_at) !== day(message.created_at)
        const grouped =
          !newDay &&
          prior.author_id === message.author_id &&
          prior.author_type === message.author_type &&
          utcDate(message.created_at).getTime() - utcDate(prior.created_at).getTime() < 300000
        return (
          <div key={message.id}>
            {newDay && <div className="day-divider">── {day(message.created_at)} ──</div>}
            <Message
              message={message}
              department={departments.find(
                (department) =>
                  department.id ===
                  agents.find((agent) => agent.id === message.author_id)?.department_id,
              )}
              agent={agents.find((agent) => agent.id === message.author_id)}
              grouped={grouped}
              profile={profile}
              me={me}
              flashing={flashes.includes(message.author_id ?? -1)}
            />
          </div>
        )
      })}
      <div ref={end} />
    </div>
  )
}
