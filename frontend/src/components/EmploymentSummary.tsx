import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Agent, SpendSummary } from '../api/types'
import { useModelCatalog } from './ModelPicker'

export function EmploymentSummary({ agent }: { agent: Agent }) {
  const { catalog } = useModelCatalog()
  const route = catalog?.models.find(
    (item) => item.provider === agent.provider && item.model_id === agent.model_id,
  )?.route
  const [spend, setSpend] = useState<SpendSummary | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let alive = true
    api
      .agentSpend(agent.id)
      .then((value) => {
        if (alive) setSpend(value)
      })
      .catch(() => {
        if (alive) setError('Spend unavailable')
      })
    return () => {
      alive = false
    }
  }, [agent.id, agent.status, agent.monthly_budget_usd])
  const percentage =
    Number(agent.monthly_budget_usd) > 0
      ? Math.min(100, (Number(spend?.total_usd ?? 0) / Number(agent.monthly_budget_usd)) * 100)
      : 0
  return (
    <section aria-label="Employment summary">
      <h3>EMPLOYMENT</h3>
      <p>
        {agent.harness === 'stub' ? 'stub / offline demo' : 'pi / chat-only'} ·{' '}
        {route?.label === 'via relay' ? 'via relay' : agent.provider}
      </p>
      <p className="accent">{agent.model_id}</p>
      <p className="dim">thinking: {agent.thinking_level}</p>
      <p className="dim">
        Up to {agent.max_output_tokens.toLocaleString()} output tokens per reply
      </p>
      <p>
        ${Number(spend?.total_usd ?? 0).toFixed(4)} / ${agent.monthly_budget_usd} this month
      </p>
      <div
        className="xp-track"
        role="progressbar"
        aria-label="Monthly salary used"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span style={{ width: `${percentage}%` }} />
      </div>
      <p className="dim">
        ${spend?.settled_usd ?? '0'} settled · ${spend?.held_usd ?? '0'} held · UTC month
      </p>
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
