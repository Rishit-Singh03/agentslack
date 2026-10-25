import { useRef, useState } from 'react'
import { Send } from 'lucide-react'
import type { Agent, Department } from '../api/types'

const commands = [
  { value: '/task ', label: '/task <title> @agent' },
  { value: '/topic ', label: '/topic <text>' },
  { value: '/hire', label: '/hire - add an agent' },
  { value: '/clear', label: '/clear - clear local conversation view' },
]

export function Composer({
  agents,
  departments,
  name,
  send,
  onMode,
}: {
  agents: Agent[]
  departments: Department[]
  name: string
  send: (body: string) => Promise<void>
  onMode: (mode: 'NORMAL' | 'INSERT') => void
}) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [cursor, setCursor] = useState(0)
  const [selection, setSelection] = useState(0)
  const [dismissed, setDismissed] = useState(false)
  const input = useRef<HTMLTextAreaElement>(null)
  const match = text.slice(0, cursor).match(/(?:^|\s)@([a-z0-9_]*)$/i)
  const options = dismissed
    ? []
    : match
      ? agents
          .filter((agent) => agent.handle.startsWith(`@${match[1].toLowerCase()}`))
          .map((agent) => ({
            value: `${agent.handle} `,
            label: `${agent.handle} [${departments.find((department) => department.id === agent.department_id)?.name ?? 'unassigned'}]`,
          }))
      : /^\/[a-z]*$/.test(text)
        ? commands.filter((command) => command.value.startsWith(text))
        : []
  const choose = (value: string) => {
    const start = match ? text.slice(0, cursor).lastIndexOf('@') : 0
    const next = text.slice(0, start) + value + text.slice(cursor)
    const position = start + value.length
    setText(next)
    setCursor(position)
    setSelection(0)
    setDismissed(true)
    requestAnimationFrame(() => {
      input.current?.focus()
      input.current?.setSelectionRange(position, position)
    })
  }
  const submit = async () => {
    if (!text.trim() || sending) return
    setSending(true)
    setError('')
    try {
      await send(text.trim())
      setText('')
      setCursor(0)
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setSending(false)
      input.current?.focus()
    }
  }
  return (
    <div className="composer-wrap">
      <div className="composer">
        {options.length > 0 && (
          <div className="completion-menu" role="listbox" aria-label="Completions">
            {options.map((option, index) => (
              <button
                key={option.value}
                role="option"
                aria-selected={index === selection % options.length}
                className={index === selection % options.length ? 'selected' : ''}
                onClick={() => choose(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
        <span className="prompt">&gt;</span>
        <textarea
          ref={input}
          data-composer
          aria-label={`Message ${name}`}
          placeholder={`message ${name}`}
          value={text}
          maxLength={10000}
          onFocus={() => onMode('INSERT')}
          onBlur={() => onMode('NORMAL')}
          onChange={(event) => {
            setText(event.target.value)
            setCursor(event.target.selectionStart)
            setSelection(0)
            setDismissed(false)
          }}
          onSelect={(event) => setCursor(event.currentTarget.selectionStart)}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) return
            if (event.key === 'Escape') {
              event.preventDefault()
              setDismissed(true)
              input.current?.blur()
              return
            }
            if (options.length && ['ArrowDown', 'ArrowUp', 'Enter', 'Tab'].includes(event.key)) {
              event.preventDefault()
              if (event.key === 'ArrowDown')
                setSelection((current) => (current + 1) % options.length)
              else if (event.key === 'ArrowUp')
                setSelection((current) => (current - 1 + options.length) % options.length)
              else choose(options[selection % options.length].value)
            } else if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              void submit()
            }
          }}
        />
        <button
          className="icon-button send-button"
          disabled={!text.trim() || sending}
          onClick={() => void submit()}
          aria-label="Send message"
        >
          <Send size={14} strokeWidth={1.5} />
        </button>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="composer-footer">
        <span>enter send / shift+enter newline</span>
        <span>/ commands / @ mention</span>
      </div>
    </div>
  )
}
