// Normalize gateway accounting before Pi parses the final OpenAI usage chunk.
// Only bounded classifications, never URLs/headers/error bodies, leave this module.
import { writeSync } from 'node:fs'

const emit = (event) => writeSync(1, JSON.stringify(event) + '\n')
const count = (value) => (Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : 0)

export function normalizeUsage(raw) {
  const output = count(raw.completion_tokens)
  const cached = count(raw.prompt_cache_hit_tokens ?? raw.prompt_tokens_details?.cached_tokens)
  const input = Math.max(
    count(raw.prompt_tokens),
    count(raw.prompt_cache_miss_tokens) + cached,
    count(raw.total_tokens) - output,
  )
  return {
    ...raw,
    prompt_tokens: input,
    completion_tokens: output,
    total_tokens: input + output,
    prompt_tokens_details: { ...raw.prompt_tokens_details, cached_tokens: Math.min(cached, input) },
  }
}

export function createRelayFetch(fetcher = globalThis.fetch, report = emit) {
  return async (input, init) => {
    let response
    try {
      response = await fetcher(input, init)
    } catch (error) {
      report({
        type: 'relay.failure',
        kind: ['TimeoutError', 'AbortError'].includes(error.name) ? 'timeout' : 'connection',
      })
      throw error
    }
    if (!response.ok) {
      let code
      try {
        const body = await response.clone().json()
        code = body?.error?.code === 'model_not_found' ? 'model_not_found' : undefined
        if (body.usage) report({ type: 'relay.usage' })
      } catch {
        /* Classification does not require a parsable error body. */
      }
      report({ type: 'relay.failure', kind: 'http', status: response.status, code })
      return response
    }
    if (!response.body) return response
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    const encoder = new TextEncoder()
    let pending = ''
    const transform = (frame) =>
      frame
        .split('\n')
        .map((line) => {
          if (!line.startsWith('data:')) return line
          try {
            const chunk = JSON.parse(line.slice(5).trim())
            if (chunk.usage) {
              chunk.usage = normalizeUsage(chunk.usage)
              report({ type: 'relay.usage' })
            }
            return 'data: ' + JSON.stringify(chunk)
          } catch {
            return line
          }
        })
        .join('\n')
    const body = new ReadableStream({
      async pull(controller) {
        try {
          const { value, done } = await reader.read()
          pending += done ? decoder.decode() : decoder.decode(value, { stream: true })
          pending = pending.replaceAll('\r\n', '\n')
          let boundary
          while ((boundary = pending.indexOf('\n\n')) >= 0) {
            controller.enqueue(encoder.encode(transform(pending.slice(0, boundary)) + '\n\n'))
            pending = pending.slice(boundary + 2)
          }
          if (done) {
            if (pending) controller.enqueue(encoder.encode(transform(pending)))
            controller.close()
          }
        } catch (error) {
          report({
            type: 'relay.failure',
            kind: error.name === 'TimeoutError' ? 'timeout' : 'connection',
          })
          controller.error(error)
        }
      },
      cancel(reason) {
        return reader.cancel(reason)
      },
    })
    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    })
  }
}
