import { useRef, useState } from 'react'
import { AtSign, Send, Sparkles } from 'lucide-react'
import type { Agent } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export function Composer({
  agents,
  name,
  send,
}: {
  agents: Agent[]
  name: string
  send: (body: string) => Promise<void>
}) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [cursor, setCursor] = useState(0)
  const [selection, setSelection] = useState(0)
  const input = useRef<HTMLTextAreaElement>(null)
  const match = text.slice(0, cursor).match(/(?:^|\s)@([a-z0-9_]*)$/i)
  const matches = match
    ? agents.filter((a) => a.handle.startsWith(`@${match[1].toLowerCase()}`))
    : []
  const mention = (agent: Agent) => {
    const start = text.slice(0, cursor).lastIndexOf('@')
    const value = `${text.slice(0, start)}${agent.handle} ${text.slice(cursor)}`
    const position = start + agent.handle.length + 1
    setText(value)
    setCursor(position)
    setSelection(0)
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
      await send(text)
      setText('')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSending(false)
      input.current?.focus()
    }
  }
  return (
    <div className="composer-wrap">
      <div className="composer">
        {matches.length > 0 && (
          <div className="mention-menu" role="listbox" aria-label="Mention an agent">
            {matches.map((a, i) => (
              <button
                key={a.id}
                className={i === selection % matches.length ? 'selected' : ''}
                onClick={() => mention(a)}
                role="option"
                aria-selected={i === selection % matches.length}
              >
                <AgentAvatar agent={a} size={26} />
                <strong>{a.name}</strong>
                <span>{a.handle}</span>
              </button>
            ))}
          </div>
        )}
        <textarea
          ref={input}
          aria-label={`Message ${name}`}
          placeholder={`Message ${name}…`}
          value={text}
          maxLength={10000}
          onChange={(e) => {
            setText(e.target.value)
            setCursor(e.target.selectionStart)
            setSelection(0)
          }}
          onSelect={(e) => setCursor(e.currentTarget.selectionStart)}
          onKeyDown={(e) => {
            if (e.nativeEvent.isComposing) return
            if (
              matches.length &&
              ['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(e.key)
            ) {
              e.preventDefault()
              if (e.key === 'ArrowDown') setSelection((s) => (s + 1) % matches.length)
              else if (e.key === 'ArrowUp')
                setSelection((s) => (s - 1 + matches.length) % matches.length)
              else if (e.key === 'Escape') setCursor(0)
              else mention(matches[selection % matches.length])
            } else if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void submit()
            }
          }}
        />
        <div className="composer-tools">
          <span className="format-hint">
            <b>B</b>
            <i>I</i>
            <span>↗</span>
            <code>&lt;/&gt;</code>
          </span>
          <button
            className="icon-button"
            aria-label="Mention an agent"
            onClick={() => {
              setText((t) => `${t}${t && !t.endsWith(' ') ? ' ' : ''}@`)
              requestAnimationFrame(() => {
                input.current?.focus()
                setCursor(input.current?.value.length ?? 0)
              })
            }}
          >
            <AtSign size={17} />
          </button>
          <span className="composer-ai">
            <Sparkles size={12} /> A whole team, one message away
          </span>
          <button
            className="send-button"
            disabled={!text.trim() || sending}
            onClick={() => void submit()}
            aria-label="Send message"
          >
            <Send size={17} />
          </button>
        </div>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="composer-footer">
        <span>
          <strong>Enter</strong> to send · <strong>Shift + Enter</strong> for a new line
        </span>
        <span>
          Try mentioning <strong>@an-agent</strong>
        </span>
      </div>
    </div>
  )
}
