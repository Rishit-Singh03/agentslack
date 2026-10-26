// Opt-in real relay/browser check. Makes three short agent requests, never logs keys.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, rm } from 'node:fs/promises'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

if (process.env.AGENTSLACK_LIVE !== '1')
  throw new Error('Set AGENTSLACK_LIVE=1 to authorize live relay screenshots')
const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backend = path.join(path.dirname(frontend), 'backend')
const artifacts = path.join(frontend, '.artifacts')
const temporary = path.join(artifacts, `relay-live-${process.pid}`)
await mkdir(temporary, { recursive: true })
const children = []
let context
let deltas = 0

async function port() {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const value = server.address().port
      server.close(() => resolve(value))
    })
  })
}
function start(command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: 'ignore' })
  children.push(child)
  return child
}
async function ready(url) {
  for (let index = 0; index < 150; index++) {
    try {
      if ((await fetch(url)).ok) return
    } catch {
      /* Startup pending. */
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error('Local live-check server did not start')
}

try {
  const backendPort = await port()
  const frontendPort = await port()
  const api = `http://127.0.0.1:${backendPort}`
  const app = `http://127.0.0.1:${frontendPort}`
  const env = { ...process.env, TEMP: temporary, TMP: temporary }
  start(
    path.join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'),
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    backend,
    {
      ...env,
      DATABASE_URL: `sqlite:///${path.join(temporary, 'live.db').replaceAll('\\', '/')}`,
      RUNTIME_DATA_DIR: path.join(temporary, 'runtime'),
    },
  )
  start(
    process.execPath,
    [
      'node_modules/vite/bin/vite.js',
      '--host',
      '127.0.0.1',
      '--port',
      String(frontendPort),
      '--strictPort',
    ],
    frontend,
    { ...env, AGENTSLACK_BACKEND_URL: api },
  )
  await Promise.all([ready(`${api}/api/health`), ready(app)])
  const executablePath =
    process.env.CHROME_PATH ??
    [
      'C:/Program Files/Google/Chrome/Application/chrome.exe',
      'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    ].find(existsSync)
  context = await chromium.launchPersistentContext(path.join(temporary, 'browser'), {
    ...(executablePath ? { executablePath } : {}),
    headless: true,
    viewport: { width: 1440, height: 960 },
    env,
  })
  const request = context.request
  assert.equal(
    (
      await request.post(`${api}/api/onboarding`, {
        data: {
          name: 'Relay verification',
          display_name: 'Sam',
          handle: '@sam',
          sample_team: true,
        },
      })
    ).status(),
    200,
  )
  const people = await (await request.get(`${api}/api/agents`)).json()
  const models = await (await request.get(`${api}/api/models`)).json()
  const choices = [
    ['@evan', 'deepseek', 'deepseek-flash', 'deepseek-v4.1-flash-1017', 'relay-deepseek'],
    ['@omar', 'openai', 'gpt-6-luna', 'gpt-6-luna', 'relay-luna'],
    ['@alice', 'anthropic', 'claude-haiku-5-5', 'claude-haiku-5-5', 'relay-haiku-unavailable'],
  ]
  for (const [handle, provider, model] of choices) {
    assert.equal(
      models.models.find((item) => item.provider === provider && item.model_id === model).route
        .provider,
      'relay',
    )
    const agent = people.find((item) => item.handle === handle)
    assert.equal(
      (
        await request.patch(`${api}/api/agents/${agent.id}`, {
          data: {
            harness: 'pi',
            provider,
            model_id: model,
            thinking_level: 'off',
            max_output_tokens: 32,
            monthly_budget_usd: '1',
          },
        })
      ).status(),
      200,
    )
  }
  const page = await context.newPage()
  page.setDefaultTimeout(90000)
  page.on('websocket', (socket) =>
    socket.on('framereceived', (frame) => {
      try {
        if (JSON.parse(String(frame.payload)).type === 'message.delta') deltas++
      } catch {
        /* Ignore other frames. */
      }
    }),
  )
  await page.goto(app)
  await page.getByRole('heading', { name: '#general', exact: true }).waitFor()
  await page.locator('.topbar .connection').filter({ hasText: 'connected' }).waitFor()
  for (const [handle, , , routedModel, filename] of choices) {
    const before = deltas
    await page.locator('[data-composer]').fill(`${handle} Reply with exactly: relay connected`)
    await page.getByRole('button', { name: 'Send message', exact: true }).click()
    if (handle !== '@alice') {
      await page
        .locator('.message-meta')
        .filter({ hasText: routedModel })
        .filter({ hasText: 'list price' })
        .waitFor()
      assert.ok(deltas > before, 'Expected visible streamed relay text')
    } else {
      await page
        .getByText(/claude-haiku-5-5: The relay reports this model is temporarily unavailable/)
        .waitFor()
    }
    await page.evaluate(() => document.fonts.ready)
    await page.screenshot({ path: path.join(artifacts, `${filename}.png`), fullPage: true })
    console.log(`live screenshot: ${filename}.png`)
  }
  const spend = await (await request.get(`${api}/api/org/spend`)).json()
  console.log(
    `Browser live check: streamed replies=${deltas} delta events; settled=${spend.recent.filter((row) => row.state === 'settled').length}; released=${spend.recent.filter((row) => row.state === 'released').length}; Haiku unavailable without substitution.`,
  )
} finally {
  await context?.close()
  for (const child of children) {
    if (child.exitCode !== null) continue
    if (process.platform === 'win32') {
      await new Promise((resolve) => {
        const stop = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
          windowsHide: true,
          stdio: 'ignore',
        })
        stop.on('exit', resolve)
      })
    } else child.kill()
  }
  assert.ok(path.resolve(temporary).startsWith(`${artifacts}${path.sep}`))
  await rm(temporary, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 })
}
