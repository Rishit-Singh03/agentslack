import { useState } from 'react'
import { Search, X } from 'lucide-react'
import type { Agent, Channel } from '../api/types'

interface SearchBoxProps {
  agents: Agent[]
  channels: Channel[]
  selectChannel: (channel: Channel) => void
  selectAgent: (agent: Agent) => void
}

export function SearchBox({ agents, channels, selectChannel, selectAgent }: SearchBoxProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const search = query.toLowerCase()
  const matchingChannels = channels.filter((channel) => channel.name.toLowerCase().includes(search))
  const matchingAgents = agents.filter((agent) =>
    `${agent.name} ${agent.role} ${agent.skills.join(' ')}`.toLowerCase().includes(search),
  )

  const close = () => {
    setOpen(false)
    setQuery('')
  }

  return (
    <div className="search-container">
      <Search size={16} />
      <input
        aria-label="Search agents and channels"
        placeholder="Find a teammate or channel…"
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value)
          setOpen(true)
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false)
        }}
      />
      <span className="search-label">YOUR WORKSPACE</span>
      {open && query && (
        <div className="search-results">
          <button className="search-close icon-button" onClick={close} aria-label="Close search">
            <X size={14} />
          </button>
          {matchingChannels.map((channel) => (
            <button
              key={channel.id}
              onClick={() => {
                selectChannel(channel)
                close()
              }}
            >
              # {channel.name}
              <small>Channel</small>
            </button>
          ))}
          {matchingAgents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => {
                selectAgent(agent)
                close()
              }}
            >
              {agent.name}
              <small>{agent.role}</small>
            </button>
          ))}
          {!matchingAgents.length && !matchingChannels.length && (
            <p>No teammates or channels found.</p>
          )}
        </div>
      )}
    </div>
  )
}
