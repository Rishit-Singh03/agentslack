import type { Org } from '../api/types'
import { ModelPicker, useModelCatalog } from './ModelPicker'

export function ModelsBudgetSettings({
  org,
  change,
}: {
  org: Org
  change: (value: Partial<Org>) => void
}) {
  const { catalog, error } = useModelCatalog()
  return (
    <section className="settings-section" aria-label="Models and budget settings">
      <h2>MODELS &amp; BUDGET</h2>
      <ModelPicker
        catalog={catalog}
        provider={org.default_provider}
        model={org.default_model_id}
        label="Default model"
        change={(provider, model) =>
          change({ default_provider: provider, default_model_id: model })
        }
      />
      <label>
        Organization monthly budget (USD)
        <input
          type="number"
          min="0"
          max="10000000"
          step="0.00000001"
          required
          value={org.org_monthly_budget_usd}
          onChange={(event) => change({ org_monthly_budget_usd: event.target.value })}
        />
      </label>
      <p className="dim">
        New custom-department employees use this default. Existing employees retain their model.
        Budget periods use UTC; unresolved usage remains held.
      </p>
      <div className="provider-status" aria-label="Provider key status">
        {catalog?.providers.map((provider) => (
          <p key={provider.id}>
            <span className={provider.configured ? 'ok' : 'dim'}>
              {provider.configured ? '[configured]' : '[missing]'}
            </span>{' '}
            {provider.id}
            <small>{provider.env_var}</small>
          </p>
        ))}
      </div>
      {catalog?.relay_base_url && <p className="dim">Relay base URL: {catalog.relay_base_url}</p>}
      {catalog?.relay_reserve_url && (
        <p className="dim">Reserve relay URL: {catalog.relay_reserve_url}</p>
      )}
      <p className="dim">
        Keys are read from backend .env. Key values are never sent to the browser.
      </p>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
    </section>
  )
}
