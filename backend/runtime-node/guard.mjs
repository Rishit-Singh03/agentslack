// Pinned to Pi 1.4.0. RPC does not expose active tools or a per-prompt output cap.
// This trusted preload asserts chat-only state and bounds the provider stream.
import { AgentSession } from '@earendil-works/pi-coding-agent'
import { writeSync } from 'node:fs'
import { createRelayFetch } from './relay-fetch.mjs'

const subscribe = AgentSession.prototype.subscribe
const prompt = AgentSession.prototype.prompt
const guarded = new WeakSet()
const calls = new WeakMap()

export function withOutputLimit(stream, maxOutputTokens) {
  if (!Number.isSafeInteger(maxOutputTokens) || maxOutputTokens < 1) {
    throw new Error('Invalid employee output token limit')
  }
  return (model, context, options) =>
    stream(model, context, {
      ...options,
      maxTokens: Math.min(maxOutputTokens, model.maxTokens),
      maxRetries: 0,
      ...(model.provider === 'relay' ? { fetch: createRelayFetch(options?.fetch) } : {}),
    })
}

AgentSession.prototype.subscribe = function (listener) {
  if (!guarded.has(this)) {
    const tools = this.getActiveToolNames()
    if (tools.length) throw new Error('Chat-only policy: tools must be empty')
    const stream = withOutputLimit(
      this.agent.streamFunction,
      Number(process.env.AGENTSLACK_MAX_OUTPUT_TOKENS ?? 4096),
    )
    this.agent.streamFunction = (model, context, options) => {
      if (this.getActiveToolNames().length || calls.get(this) !== 0) {
        throw new Error('Chat-only policy: additional provider requests are disabled')
      }
      calls.set(this, 1)
      return stream(model, context, options)
    }
    guarded.add(this)
    // Pi redirects ordinary stdout during startup; write to the protocol fd directly.
    writeSync(1, JSON.stringify({ type: 'runtime.ready', tools }) + '\n')
  }
  return subscribe.call(this, listener)
}

AgentSession.prototype.prompt = function (...args) {
  calls.set(this, 0)
  return prompt.apply(this, args)
}
