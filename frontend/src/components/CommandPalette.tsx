import { useEffect, useRef, useState } from 'react'
import { Modal } from './Modal'

export interface Command {
  id: string
  label: string
  category: string
  run: () => void
}

function fuzzyMatch(query: string, value: string): boolean {
  let position = 0
  for (const letter of value.toLowerCase()) {
    if (letter === query[position]) position++
  }
  return position === query.length
}

export function CommandPalette({ commands, close }: { commands: Command[]; close: () => void }) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const results = commands.filter((command) =>
    fuzzyMatch(query.toLowerCase().replace(/\s/g, ''), command.label),
  )
  const list = useRef<HTMLDivElement>(null)
  useEffect(() => {
    list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [selected])
  const run = (command: Command) => {
    close()
    command.run()
  }
  return (
    <Modal
      title="command palette"
      subtitle="Jump to a channel, open a profile, or run an action."
      close={close}
    >
      <input
        className="palette-input"
        autoFocus
        aria-label="Find command"
        placeholder="> type a command"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setSelected(0)
        }}
        aria-controls="command-results"
        aria-activedescendant={
          results.length ? `command-${results[selected % results.length].id}` : undefined
        }
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            setSelected((index) => (results.length ? (index + 1) % results.length : 0))
          }
          if (event.key === 'ArrowUp') {
            event.preventDefault()
            setSelected((index) =>
              results.length ? (index - 1 + results.length) % results.length : 0,
            )
          }
          if (event.key === 'Enter' && results.length) {
            event.preventDefault()
            run(results[selected % results.length])
          }
        }}
      />
      <div
        className="command-results"
        id="command-results"
        role="listbox"
        ref={list}
        aria-label="Commands"
      >
        {results.map((command, index) => (
          <button
            id={`command-${command.id}`}
            key={command.id}
            role="option"
            aria-selected={index === selected % results.length}
            onClick={() => run(command)}
          >
            <span>{command.label}</span>
            <small>{command.category}</small>
          </button>
        ))}
        {!results.length && <p className="empty-state">No matching commands.</p>}
      </div>
      <p className="keyboard-hint">↑ ↓ select · enter run · esc close</p>
    </Modal>
  )
}
