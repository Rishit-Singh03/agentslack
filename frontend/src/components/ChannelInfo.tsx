import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Channel } from '../api/types'

export function ChannelInfo({
  channel,
  close,
  changed,
  removed,
}: {
  channel: Channel
  close: () => void
  changed: (channel: Channel) => void
  removed: (id: number) => void
}) {
  const [confirm, setConfirm] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      changed(
        await api.updateChannel(channel.id, {
          name: String(data.get('name')),
          topic: String(data.get('topic')),
        }),
      )
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const remove = async () => {
    try {
      await api.deleteChannel(channel.id)
      removed(channel.id)
      close()
    } catch (error) {
      setError((error as Error).message)
    }
  }
  return (
    <aside className="info-pane">
      <header>
        <h2>channel / #{channel.name}</h2>
        <button onClick={close} aria-label="Close channel info">
          [x]
        </button>
      </header>
      <div className="pane-scroll">
        {channel.is_dm ? (
          <p>Direct conversation. Open the agent profile to edit its settings.</p>
        ) : (
          <form className="pane-form" onSubmit={submit}>
            <label>
              Name
              <input
                name="name"
                defaultValue={channel.name}
                readOnly={channel.name === 'general'}
                required
                pattern="[a-z0-9][a-z0-9-]{0,49}"
              />
            </label>
            <label>
              Topic
              <textarea name="topic" defaultValue={channel.topic} rows={4} maxLength={500} />
            </label>
            <button className="primary-button" disabled={busy}>
              Save channel
            </button>
          </form>
        )}
        <section>
          <h3>MEMBERS</h3>
          <p>{channel.member_ids?.length ?? 0} registered members</p>
        </section>
        {channel.name !== 'general' && (
          <section>
            <h3>MANAGE</h3>
            {confirm ? (
              <>
                <p>
                  Delete this channel and its messages? Tasks will be retained without a channel.
                </p>
                <div className="pane-actions">
                  <button className="danger" onClick={() => void remove()}>
                    [confirm delete]
                  </button>
                  <button onClick={() => setConfirm(false)}>[cancel]</button>
                </div>
              </>
            ) : (
              <button className="danger" onClick={() => setConfirm(true)}>
                [delete channel]
              </button>
            )}
          </section>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </aside>
  )
}
