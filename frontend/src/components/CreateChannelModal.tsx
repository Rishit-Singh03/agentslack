import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Channel } from '../api/types'
import { Modal } from './Modal'

export function CreateChannelModal({
  close,
  created,
}: {
  close: () => void
  created: (channel: Channel) => void
}) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      created(
        await api.createChannel({
          name: String(data.get('name')),
          topic: String(data.get('topic')),
        }),
      )
      close()
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal
      title="new channel"
      subtitle="Channel names use lowercase letters, numbers, and hyphens."
      close={close}
    >
      <form onSubmit={submit}>
        <label>
          Name
          <input
            name="name"
            required
            pattern="[a-z0-9][a-z0-9-]{0,49}"
            placeholder="project-name"
            autoFocus
          />
        </label>
        <label>
          Topic
          <textarea name="topic" rows={3} maxLength={500} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" onClick={close}>
            [cancel]
          </button>
          <button className="primary-button" disabled={busy}>
            Create channel
          </button>
        </div>
      </form>
    </Modal>
  )
}
