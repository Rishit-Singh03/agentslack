import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ModelCatalog } from '../api/types'

export function useModelCatalog() {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let alive = true
    api
      .models()
      .then((value) => {
        if (alive) setCatalog(value)
      })
      .catch(() => {
        if (alive) setError('Model catalog unavailable. Try reopening this view.')
      })
    return () => {
      alive = false
    }
  }, [])
  return { catalog, error }
}

export function ModelPicker({
  catalog,
  provider,
  model,
  change,
  label = 'Model',
  maxOutputTokens = 4096,
}: {
  catalog: ModelCatalog | null
  provider: string
  model: string
  change: (provider: string, model: string) => void
  label?: string
  maxOutputTokens?: number
}) {
  const selected = catalog?.models.find(
    (item) => item.provider === provider && item.model_id === model,
  )
  const [custom, setCustom] = useState(false)
  const keyStatus = catalog?.providers.find((item) => item.id === provider)
  return (
    <div className="model-picker">
      <label>
        {label}
        <select
          aria-label={label}
          value={custom || (!selected && catalog) ? 'custom' : `${provider}|${model}`}
          onChange={(event) => {
            if (event.target.value === 'custom') {
              setCustom(true)
              return
            }
            setCustom(false)
            const [nextProvider, nextModel] = event.target.value.split('|')
            change(nextProvider, nextModel)
          }}
        >
          {!catalog && <option value={`${provider}|${model}`}>{model}</option>}
          {catalog?.models.map((item) => (
            <option
              key={`${item.provider}|${item.model_id}`}
              value={`${item.provider}|${item.model_id}`}
            >
              {item.name} / {item.route.label === 'via relay' ? 'via relay' : item.provider} · $
              {item.input} in / ${item.output} out per 1M
            </option>
          ))}
          <option value="custom">Custom ID (validated pricing required to run)</option>
        </select>
      </label>
      {(custom || (!selected && catalog)) && (
        <div className="form-row">
          <label>
            Provider
            <select value={provider} onChange={(event) => change(event.target.value, model)}>
              {catalog?.providers.map((item) => (
                <option key={item.id}>{item.id}</option>
              ))}
            </select>
          </label>
          <label>
            Custom model ID
            <input
              value={model}
              required
              maxLength={150}
              onChange={(event) => change(provider, event.target.value)}
            />
          </label>
        </div>
      )}
      <p className="dim">
        {keyStatus
          ? selected?.route.configured
            ? `${selected.route.label} · configured`
            : `${provider}: key missing — set ${keyStatus.env_var} or configure the relay`
          : 'Loading provider status…'}
      </p>
      {selected && (
        <p className="dim model-help">
          Reserves up to {Math.min(maxOutputTokens, selected.max_output).toLocaleString()} output
          tokens per reply.
          {selected.route.provider === 'relay' && ' Costs use list prices.'}
        </p>
      )}
    </div>
  )
}
