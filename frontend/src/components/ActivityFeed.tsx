import { useEffect, useRef } from 'react'
import type { Activity } from '../api/types'
import { clockTime } from '../utils'

export function ActivityFeed({ entries }: { entries: Activity[] }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [entries.length])
  return (
    <>
      <header className="view-header">
        <h1>activity</h1>
        <span className="topic">tail -f workspace.events</span>
        <span className="header-action">{entries.length} events</span>
      </header>
      <div className="activity-feed" role="log" aria-label="Activity feed">
        <p className="dim"># session log — events are retained in this tab</p>
        {entries.map((entry) => (
          <div className="activity-entry" key={entry.id}>
            <time>{clockTime(entry.time, true)}</time>
            <span>{entry.text}</span>
          </div>
        ))}
        {!entries.length && (
          <p className="empty-state">No events yet. Post a message or update a task.</p>
        )}
        <div ref={end} />
      </div>
    </>
  )
}
