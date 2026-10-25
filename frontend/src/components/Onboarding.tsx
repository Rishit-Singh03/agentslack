import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { DepartmentDraft, DepartmentTemplate } from '../api/types'
import { AccentPicker } from './AppearanceFields'
import { DepartmentChooser } from './DepartmentChooser'

export function Onboarding({ initialized }: { initialized: () => Promise<void> }) {
  const [step, setStep] = useState<'workspace' | 'departments'>('workspace')
  const [accent, setAccent] = useState('#3ddc84')
  const [config, setConfig] = useState({
    name: '',
    display_name: '',
    handle: '',
    sample_team: true,
  })
  const [catalog, setCatalog] = useState<DepartmentTemplate[]>([])
  const [selected, setSelected] = useState<DepartmentDraft[]>([])
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let alive = true
    api
      .departmentCatalog()
      .then((items) => {
        if (!alive) return
        setCatalog(items)
        setSelected(
          items.filter((item) => item.core).map((item, index) => ({ ...item, sort_order: index })),
        )
        setLoaded(true)
      })
      .catch((error) => {
        if (alive) setError(error.message)
      })
    return () => {
      alive = false
    }
  }, [])
  const next = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const handle = String(fields.get('handle')).trim().replace(/^@/, '').toLowerCase()
    setConfig({
      name: String(fields.get('org')).trim(),
      display_name: String(fields.get('name')).trim(),
      handle: `@${handle}`,
      sample_team: fields.get('team') === 'sample',
    })
    setStep('departments')
  }
  const initialize = async () => {
    setBusy(true)
    setError('')
    try {
      await api.onboard({
        ...config,
        accent,
        departments: selected.map((item, index) => ({ ...item, sort_order: index })),
      })
      await initialized()
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="onboarding">
      <div className={`setup-panel ${step === 'departments' ? 'setup-departments' : ''}`}>
        <header>
          <span>agentslack</span>
          <span className="dim">
            setup / {step === 'workspace' ? '01 workspace' : '02 departments'}
          </span>
        </header>
        <div className="setup-body">
          <h1>
            <span className="accent">$</span> agentslack init
            {step === 'departments' ? ' / departments' : ''}
          </h1>
          {step === 'workspace' ? (
            <>
              <p>Configure this workspace. Choose its departments in the next step.</p>
              <form onSubmit={next}>
                <label>
                  Organization name
                  <input
                    name="org"
                    required
                    maxLength={100}
                    defaultValue={config.name}
                    placeholder="acme"
                    autoFocus
                  />
                </label>
                <div className="form-row">
                  <label>
                    Your name
                    <input
                      name="name"
                      required
                      maxLength={100}
                      defaultValue={config.display_name}
                      placeholder="Your name"
                    />
                  </label>
                  <label>
                    Your handle
                    <input
                      name="handle"
                      required
                      pattern="@?[a-zA-Z][a-zA-Z0-9_]{0,30}"
                      defaultValue={config.handle}
                      placeholder="@you"
                    />
                  </label>
                </div>
                <div className="field-group">
                  <span>Accent</span>
                  <AccentPicker value={accent} change={setAccent} />
                </div>
                <fieldset>
                  <legend>INITIAL DATA</legend>
                  <label className="checkbox-label">
                    <input
                      type="radio"
                      name="team"
                      value="sample"
                      defaultChecked={config.sample_team}
                    />
                    start with sample team{' '}
                    <span className="dim">one agent per selected core department</span>
                  </label>
                  <label className="checkbox-label">
                    <input
                      type="radio"
                      name="team"
                      value="empty"
                      defaultChecked={!config.sample_team}
                    />
                    start empty <span className="dim">channels and departments only</span>
                  </label>
                </fieldset>
                <button className="primary-button" disabled={!loaded}>
                  Next: departments
                </button>
              </form>
            </>
          ) : (
            <>
              <DepartmentChooser catalog={catalog} selected={selected} change={setSelected} />
              <div className="setup-actions">
                <button onClick={() => setStep('workspace')}>[back]</button>
                <button
                  className="primary-button"
                  disabled={busy}
                  onClick={() => void initialize()}
                >
                  {busy ? 'initializing...' : 'Initialize workspace'}
                </button>
              </div>
            </>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </div>
        <footer>Org channels: #general / #announcements / #standup / #requests / #random</footer>
      </div>
    </main>
  )
}
