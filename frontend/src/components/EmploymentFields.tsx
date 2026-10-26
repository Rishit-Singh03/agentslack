import { useState } from 'react'
import type { Agent } from '../api/types'
import { ModelPicker, useModelCatalog } from './ModelPicker'

export function employmentFromForm(data: FormData) {
  return {
    harness: String(data.get('harness')) as Agent['harness'],
    provider: String(data.get('provider')),
    model_id: String(data.get('model_id')),
    thinking_level: String(data.get('thinking_level')),
    max_output_tokens: Number(data.get('max_output_tokens')),
    monthly_budget_usd: String(data.get('monthly_budget_usd')),
  }
}

export function EmploymentFields({ agent }: { agent: Agent }) {
  const { catalog, error } = useModelCatalog()
  const [provider, setProvider] = useState(agent.provider)
  const [model, setModel] = useState(agent.model_id)
  const [thinking, setThinking] = useState(agent.thinking_level)
  const [maxOutput, setMaxOutput] = useState(agent.max_output_tokens)
  const selected = catalog?.models.find(
    (item) => item.provider === provider && item.model_id === model,
  )
  const levels = catalog?.models.find(
    (item) => item.provider === provider && item.model_id === model,
  )?.thinking_levels ?? ['off']
  return (
    <fieldset className="employment-fields">
      <legend>Employment</legend>
      <label>
        Harness
        <select name="harness" aria-label="Harness" defaultValue={agent.harness}>
          <option value="pi">pi / live chat</option>
          <option value="stub">stub / offline demo</option>
        </select>
      </label>
      <ModelPicker
        catalog={catalog}
        provider={provider}
        model={model}
        maxOutputTokens={maxOutput}
        change={(nextProvider, nextModel) => {
          setProvider(nextProvider)
          setModel(nextModel)
          setThinking('off')
          const next = catalog?.models.find(
            (item) => item.provider === nextProvider && item.model_id === nextModel,
          )
          setMaxOutput((current) => Math.min(current, next?.max_output ?? 4096))
        }}
      />
      <input type="hidden" name="provider" value={provider} />
      <input type="hidden" name="model_id" value={model} />
      <label>
        Thinking level
        <select
          name="thinking_level"
          aria-label="Thinking level"
          value={thinking}
          onChange={(event) => setThinking(event.target.value)}
        >
          {levels.map((level) => (
            <option key={level}>{level}</option>
          ))}
        </select>
      </label>
      <label>
        Maximum output tokens
        <input
          name="max_output_tokens"
          type="number"
          min="1"
          max={selected?.max_output ?? 384000}
          step="1"
          required
          value={maxOutput}
          onChange={(event) => setMaxOutput(Number(event.target.value))}
        />
      </label>
      <label>
        Monthly salary (USD)
        <input
          name="monthly_budget_usd"
          type="number"
          min="0"
          max="1000000"
          step="0.00000001"
          defaultValue={agent.monthly_budget_usd}
          required
        />
      </label>
      <p className="dim">
        A spending allowance, reset monthly in UTC. Held and unresolved reservations count against
        it.
      </p>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
    </fieldset>
  )
}
