import { DepartmentSettings } from './DepartmentSettings'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Department, Org, UserProfile } from '../api/types'
import { AppearanceFields } from './AppearanceFields'
import { ModelsBudgetSettings } from './ModelsBudgetSettings'

export function SettingsView({
  org,
  departments,
  departmentChanged,
  departmentRemoved,
  me,
  preview,
  saved,
}: {
  org: Org
  departments: Department[]
  departmentChanged: (department: Department) => void
  departmentRemoved: (id: number) => void
  me: UserProfile
  preview: (org: Org | null) => void
  saved: (org: Org, me: UserProfile) => void
}) {
  const [draft, setDraft] = useState(org)
  const [profile, setProfile] = useState(me)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    setDraft(org)
    preview(null)
  }, [org, preview])
  useEffect(() => {
    setProfile(me)
  }, [me])
  useEffect(() => () => preview(null), [preview])
  const change = (changes: Partial<Org>) => {
    const next = { ...draft, ...changes }
    setDraft(next)
    setStatus('Unsaved changes')
    preview({ ...next, accent: /^#[0-9a-f]{6}$/i.test(next.accent) ? next.accent : org.accent })
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setStatus('Saving...')
    try {
      const updatedOrg = await api.updateOrg({
        name: draft.name,
        tagline: draft.tagline,
        accent: draft.accent,
        theme: draft.theme,
        density: draft.density,
        font_mode: draft.font_mode,
        crt_effects: draft.crt_effects,
        default_provider: draft.default_provider,
        default_model_id: draft.default_model_id,
        org_monthly_budget_usd: draft.org_monthly_budget_usd,
      })
      const updatedProfile = await api.updateMe({
        display_name: profile.display_name,
        handle: profile.handle,
      })
      saved(updatedOrg, updatedProfile)
      preview(null)
      setStatus('Saved')
    } catch (error) {
      setStatus((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <header className="view-header">
        <h1>settings</h1>
        <span className="topic">workspace configuration</span>
        <span className="header-action">/settings</span>
      </header>
      <div className="settings-scroll">
        <div className="settings-main">
          <form className="settings-form" onSubmit={submit}>
            <section className="settings-section">
              <h2>ORG</h2>
              <label>
                Organization name
                <input
                  value={draft.name}
                  required
                  maxLength={100}
                  onChange={(event) => change({ name: event.target.value })}
                />
              </label>
              <label>
                Tagline
                <input
                  value={draft.tagline}
                  maxLength={200}
                  onChange={(event) => change({ tagline: event.target.value })}
                />
              </label>
              <p className="dim">slug: {draft.slug} (derived from name on save)</p>
            </section>
            <AppearanceFields org={draft} change={change} />
            <ModelsBudgetSettings org={draft} change={change} />
            <section className="settings-section">
              <h2>PROFILE</h2>
              <div className="form-row">
                <label>
                  Display name
                  <input
                    value={profile.display_name}
                    required
                    maxLength={100}
                    onChange={(event) =>
                      setProfile({ ...profile, display_name: event.target.value })
                    }
                  />
                </label>
                <label>
                  Handle
                  <input
                    value={profile.handle}
                    required
                    pattern="@[a-z][a-z0-9_]{0,30}"
                    onChange={(event) => setProfile({ ...profile, handle: event.target.value })}
                  />
                </label>
              </div>
            </section>
            <div className="settings-actions">
              <button className="primary-button" disabled={busy}>
                Save settings
              </button>
              <button
                type="button"
                onClick={() => {
                  setDraft(org)
                  setProfile(me)
                  preview(null)
                  setStatus('')
                }}
              >
                [reset]
              </button>
              <span role="status">{status}</span>
            </div>
          </form>
          <DepartmentSettings
            departments={departments}
            changed={departmentChanged}
            removed={departmentRemoved}
          />
        </div>
        <aside className="settings-reference">
          <h2>PREVIEW</h2>
          <p className="accent">$ workspace.config</p>
          <dl>
            <dt>theme</dt>
            <dd>{draft.theme}</dd>
            <dt>density</dt>
            <dd>{draft.density}</dd>
            <dt>font</dt>
            <dd>{draft.font_mode}</dd>
            <dt>scanlines</dt>
            <dd>{draft.crt_effects ? 'on' : 'off'}</dd>
          </dl>
          <div className="preview-message" aria-label="Sample message preview">
            <div className="preview-message-header">
              <time>09:41</time>
              <span className="accent">{profile.handle || '@you'}</span>
              <span className="dim">#announcements</span>
            </div>
            <p>Weekly update: priorities are confirmed. Share any blockers in #standup.</p>
          </div>
          <p className="dim">Sample message using the current accent, density, and message font.</p>
          <p className="dim">
            Ctrl K command palette
            <br />
            Esc close panes
            <br />? keyboard shortcuts
          </p>
        </aside>
      </div>
    </>
  )
}
