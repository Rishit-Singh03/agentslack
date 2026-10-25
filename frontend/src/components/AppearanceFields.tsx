import type { CSSProperties } from 'react'
import type { Org } from '../api/types'

export const accents = [
  { name: 'phosphor', hex: '#3ddc84' },
  { name: 'amber', hex: '#ffb000' },
  { name: 'cyan', hex: '#56d4dd' },
  { name: 'mono', hex: '#e6e6e6' },
  { name: 'magenta', hex: '#ff5fd2' },
]

export function AccentPicker({ value, change }: { value: string; change: (hex: string) => void }) {
  return (
    <div className="accent-picker" role="group" aria-label="Accent presets">
      {accents.map((accent) => (
        <button
          type="button"
          key={accent.name}
          aria-label={accent.name}
          className={value.toLowerCase() === accent.hex ? 'selected' : ''}
          aria-pressed={value.toLowerCase() === accent.hex}
          onClick={() => change(accent.hex)}
        >
          <span className="accent-swatch" style={{ '--swatch': accent.hex } as CSSProperties} />
          {accent.name}
        </button>
      ))}
    </div>
  )
}

export function AppearanceFields({
  org,
  change,
}: {
  org: Org
  change: (changes: Partial<Org>) => void
}) {
  return (
    <section className="settings-section">
      <h2>APPEARANCE</h2>
      <div className="field-group">
        <span>Accent</span>
        <AccentPicker value={org.accent} change={(accent) => change({ accent })} />
      </div>
      <label>
        Custom hex
        <input
          aria-label="Custom accent hex"
          value={org.accent}
          pattern="#[0-9a-fA-F]{6}"
          onChange={(event) => change({ accent: event.target.value })}
        />
      </label>
      <div className="form-row">
        <label>
          Theme
          <select
            aria-label="Theme"
            value={org.theme}
            onChange={(event) => change({ theme: event.target.value as Org['theme'] })}
          >
            <option value="dark">dark</option>
            <option value="paper">paper</option>
          </select>
        </label>
        <label>
          Density
          <select
            aria-label="Density"
            value={org.density}
            onChange={(event) => change({ density: event.target.value as Org['density'] })}
          >
            <option value="compact">compact</option>
            <option value="comfortable">comfortable</option>
          </select>
        </label>
      </div>
      <label>
        Font mode
        <select
          aria-label="Font mode"
          value={org.font_mode}
          onChange={(event) => change({ font_mode: event.target.value as Org['font_mode'] })}
        >
          <option value="mixed">mixed — sans message bodies</option>
          <option value="mono">all-mono</option>
        </select>
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={org.crt_effects}
          onChange={(event) => change({ crt_effects: event.target.checked })}
        />
        CRT scanlines (optional)
      </label>
      <p className="dim">Appearance changes preview immediately. Save to apply in other tabs.</p>
    </section>
  )
}
