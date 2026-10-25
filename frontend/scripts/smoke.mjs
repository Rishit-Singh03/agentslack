import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, rm } from 'node:fs/promises'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repo = path.dirname(frontend)
const artifacts = path.join(frontend, '.artifacts')
const temporary = path.join(artifacts, 'temp')
const profile = path.join(artifacts, 'browser-profile')
const database = path.join(artifacts, `smoke-${process.pid}.db`)
await mkdir(temporary, { recursive: true })
const environment = { ...process.env, TEMP: temporary, TMP: temporary }
const processes = []
const errors = []
let context

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
  })
}

function start(command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: 'pipe' })
  child.log = ''
  child.stdout.on('data', (chunk) => (child.log = (child.log + chunk).slice(-4000)))
  child.stderr.on('data', (chunk) => (child.log = (child.log + chunk).slice(-4000)))
  child.on('error', (error) => errors.push(error.message))
  processes.push(child)
  return child
}

async function ready(url, process) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (process.exitCode !== null) throw new Error(process.log)
    try {
      if ((await fetch(url)).ok) return
    } catch {
      /* Server is still starting. */
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error(`Server did not start: ${url}\n${process.log}`)
}

async function waitForTheme(page, theme) {
  await page.waitForFunction((value) => document.documentElement.dataset.theme === value, theme)
}

try {
  const backendPort = await freePort()
  const frontendPort = await freePort()
  const apiUrl = `http://127.0.0.1:${backendPort}`
  const appUrl = `http://127.0.0.1:${frontendPort}`
  const python = path.join(
    repo,
    'backend',
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  )
  const backend = start(
    python,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    path.join(repo, 'backend'),
    { ...environment, DATABASE_URL: `sqlite:///${database.replaceAll('\\', '/')}` },
  )
  const vite = start(
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
    { ...environment, AGENTSLACK_BACKEND_URL: apiUrl },
  )
  await Promise.all([ready(`${apiUrl}/api/health`, backend), ready(appUrl, vite)])
  const executable =
    process.env.CHROME_PATH ??
    [
      'C:/Program Files/Google/Chrome/Application/chrome.exe',
      'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    ].find(existsSync)
  context = await chromium.launchPersistentContext(profile, {
    ...(executable ? { executablePath: executable } : {}),
    headless: true,
    viewport: { width: 1440, height: 960 },
    env: environment,
    downloadsPath: path.join(artifacts, 'downloads'),
  })
  const page = await context.newPage()
  page.on('pageerror', (error) => errors.push(error.message))
  page.setDefaultTimeout(15000)
  const screenshot = async (name) => {
    if (name === 'settings-dark') await page.setViewportSize({ width: 1440, height: 1720 })
    await page.evaluate(() => document.fonts.ready)
    await page.screenshot({
      path: path.join(artifacts, `${name}.png`),
      fullPage: true,
      animations: 'disabled',
    })
    console.log(`screenshot: ${name}`)
    if (name === 'settings-dark') await page.setViewportSize({ width: 1440, height: 960 })
  }
  const navigate = async (name) =>
    page
      .getByRole('navigation')
      .getByRole('button', { name: new RegExp(`^${name}(?:\\s|$)`) })
      .click()
  const command = async (query) => {
    await page.keyboard.press('Control+k')
    await page.getByLabel('Find command').fill(query)
    await page.getByLabel('Find command').press('Enter')
  }
  const send = async (body) => {
    await page.locator('[data-composer]').fill(body)
    await page.getByRole('button', { name: 'Send message', exact: true }).click()
  }
  await page.goto(appUrl)
  await page.getByRole('heading', { name: '$ agentslack init' }).waitFor()
  await screenshot('onboarding')
  await page.getByLabel('Organization name').fill('Acme Systems')
  await page.getByLabel('Your name', { exact: true }).fill('Sam')
  await page.getByLabel('Your handle').fill('@sam')
  await page.getByRole('button', { name: 'Next: departments' }).click()
  await page
    .getByRole('heading', { name: '$ agentslack init / departments', exact: true })
    .waitFor()
  assert.equal(await page.locator('.department-options input:checked').count(), 8)
  await screenshot('onboarding-departments')
  await page.getByRole('checkbox', { name: /^Research/ }).check()
  await page.getByRole('checkbox', { name: /^Research/ }).uncheck()
  await page.getByRole('button', { name: '+ add custom department', exact: true }).click()
  await page.getByLabel('Department name', { exact: true }).fill('Facilities')
  await page.getByLabel('Description', { exact: true }).fill('Office and equipment coordination')
  await page.getByRole('button', { name: 'Add department', exact: true }).click()
  await page.getByRole('checkbox', { name: /^Facilities/ }).uncheck()
  await page.getByRole('checkbox', { name: /^Facilities/ }).waitFor()
  await page.getByRole('button', { name: 'Initialize workspace', exact: true }).click()
  await page.getByRole('heading', { name: '#general', exact: true }).waitFor()
  await page.locator('.topbar .connection').filter({ hasText: 'connected' }).waitFor()
  console.log('onboarding: sample workspace initialized')

  await page.keyboard.press('Control+k')
  await page.getByLabel('Find command').fill('engineer')
  await screenshot('palette')
  await page.getByLabel('Find command').press('Enter')
  await page.getByRole('heading', { name: '#engineering', exact: true }).waitFor()
  await page.keyboard.press('Alt+ArrowUp')
  await page.getByRole('heading', { name: '#product', exact: true }).waitFor()
  await page.keyboard.press('Alt+ArrowDown')
  await page.getByRole('heading', { name: '#engineering', exact: true }).waitFor()
  await command('#general')
  await page.getByRole('heading', { name: '#general', exact: true }).waitFor()
  const composer = page.locator('[data-composer]')
  await composer.fill('@eva')
  await page.getByRole('option', { name: '@evan [Engineering]' }).waitFor()
  await composer.press('Enter')
  assert.equal(await composer.inputValue(), '@evan ')
  await composer.press('End')
  await composer.pressSequentially('review service reliability')
  await composer.press('Enter')
  await page.getByLabel('Streaming reply').waitFor()
  await page.waitForFunction(
    () => Array.from(document.querySelectorAll('.message-body')).at(-1)?.textContent.length > 30,
  )
  const partial = await page.locator('.message-body').last().innerText()
  await page.locator('.message .handle').filter({ hasText: '@evan' }).first().click()
  assert.equal(
    await page
      .locator('.message .handle')
      .filter({ hasText: '@evan' })
      .first()
      .evaluate((element) => getComputedStyle(element).color),
    'rgb(112, 167, 216)',
  )
  await screenshot('workspace-dark')
  await page.getByLabel('Streaming reply').waitFor({ state: 'detached' })
  const complete = await page.locator('.message-body').last().innerText()
  assert.ok(complete.length > partial.length)
  assert.match(complete, /stub reply from Evan/)
  await page.keyboard.press('Escape')
  await send('/topic Company priorities and shared requests')
  await page.getByText('Company priorities and shared requests', { exact: true }).waitFor()
  await send('/task Browser acceptance @alice')
  await page.keyboard.press('Escape')
  await page.keyboard.press('n')
  await page.getByLabel('Task title').fill('Keyboard task')
  await page.getByRole('dialog').getByRole('button', { name: 'Create task', exact: true }).click()
  await navigate('tasks')
  const keyboardTask = page.getByRole('article', { name: 'Task Keyboard task', exact: true })
  await keyboardTask.focus()
  await keyboardTask.press('l')
  await page.waitForFunction(
    () => document.querySelector('[aria-label="Status of Keyboard task"]')?.value === 'in_progress',
  )
  const levelTask = await (
    await context.request.post(`${apiUrl}/api/tasks`, {
      data: {
        title: 'Ship pagination',
        description: 'Review the pagination contract and edge cases.',
        assignee_agent_id: 1,
        channel_id: 1,
        xp_reward: 70,
      },
    })
  ).json()
  await page.getByLabel(`Status of ${levelTask.title}`).selectOption('done')
  await page.locator('.sidebar .level-flash').waitFor()
  await screenshot('tasks-dark')
  await navigate('activity')
  await page
    .getByRole('log', { name: 'Activity feed' })
    .getByText(/lvl 3 → 4/)
    .waitFor()
  console.log('streaming, slash commands, keyboard task movement, activity, level-up: passed')
  await command('agents')
  await page.getByRole('heading', { name: 'agents', exact: true }).waitFor()
  await screenshot('agents')

  await command('new channel')
  await page.getByRole('dialog').getByLabel('Name', { exact: true }).fill('browser-test')
  await page.getByRole('dialog').getByRole('button', { name: 'Create channel' }).click()
  await page.getByRole('heading', { name: '#browser-test', exact: true }).waitFor()
  await page.keyboard.press(']')
  await page.getByLabel('Topic', { exact: true }).fill('Editable topic')
  await page.getByRole('button', { name: 'Save channel' }).click()
  await page.locator('.topic').filter({ hasText: 'Editable topic' }).waitFor()
  await page.getByRole('button', { name: '[delete channel]', exact: true }).click()
  await page.getByRole('button', { name: '[confirm delete]', exact: true }).click()
  await page.getByRole('heading', { name: '#general', exact: true }).waitFor()
  await command('hire agent')
  await page.getByRole('dialog').getByLabel('Name', { exact: true }).fill('Alex')
  await page.getByLabel('Handle', { exact: true }).fill('@alex')
  await page.getByLabel('Title', { exact: true }).fill('Operations specialist')
  await page.getByLabel('Department', { exact: true }).selectOption({ label: 'Operations' })
  await page.getByRole('dialog').getByRole('button', { name: 'Hire agent', exact: true }).click()
  await page.getByRole('button', { name: '[edit]', exact: true }).click()
  await page.getByLabel('Title', { exact: true }).fill('Delivery specialist')
  await page.getByLabel('Department', { exact: true }).selectOption('')
  await page.getByRole('button', { name: 'Save agent' }).click()
  await page.getByText('Alex - Delivery specialist', { exact: true }).waitFor()
  await page.getByRole('button', { name: '[dismiss agent]', exact: true }).click()
  await page.getByRole('button', { name: '[confirm dismiss]', exact: true }).click()
  await page
    .getByRole('navigation')
    .getByRole('button', { name: /evan engineering$/ })
    .click()
  await page.getByRole('heading', { name: '@evan', exact: true }).waitFor()
  await send('Check the DM connection')
  await page.getByLabel('Streaming reply').waitFor()
  await page.getByLabel('Streaming reply').waitFor({ state: 'detached' })
  await send('/clear')
  await page.getByText(/No messages in Evan/).waitFor()
  console.log('channel and agent editing/deletion, DM, local clear: passed')

  await command('settings')
  await page.getByRole('heading', { name: 'settings', exact: true }).waitFor()
  assert.equal(new URL(page.url()).pathname, '/settings')
  await screenshot('settings-dark')
  const departmentsRegion = page.getByRole('region', { name: 'Departments settings' })
  await departmentsRegion.getByRole('button', { name: '[+ add department]', exact: true }).click()
  await page.getByLabel('Department name', { exact: true }).fill('Facilities')
  await page.getByLabel('Department color', { exact: true }).fill('#56d4dd')
  await page.getByRole('button', { name: 'Add department', exact: true }).click()
  await page.getByRole('button', { name: 'Edit Facilities', exact: true }).click()
  await page.getByLabel('Department name', { exact: true }).fill('Workplace')
  await page.getByLabel('Department color', { exact: true }).fill('#ffb000')
  await page.getByRole('button', { name: 'Save department', exact: true }).click()
  await page.getByRole('button', { name: 'Move Workplace up', exact: true }).click()
  const departmentList = await (await context.request.get(`${apiUrl}/api/departments`)).json()
  const workplace = departmentList.find((department) => department.name === 'Workplace')
  const hired = await (
    await context.request.post(`${apiUrl}/api/agents`, {
      data: {
        name: 'Taylor',
        handle: '@taylor',
        title: 'Office Coordinator',
        department_id: workplace.id,
      },
    })
  ).json()
  await page.getByRole('button', { name: 'Remove Workplace', exact: true }).click()
  await page.getByRole('button', { name: '[confirm remove]', exact: true }).click()
  await page
    .getByRole('button', { name: 'Remove Workplace', exact: true })
    .waitFor({ state: 'detached' })
  await page
    .getByRole('navigation')
    .getByRole('button', { name: /taylor unassigned$/ })
    .waitFor()
  assert.equal((await context.request.delete(`${apiUrl}/api/agents/${hired.id}`)).status(), 204)
  console.log(
    'department catalog, custom selection, editing, colors, reorder, removal, unassignment: passed',
  )

  const secondTab = await context.newPage()
  secondTab.on('pageerror', (error) => errors.push(error.message))
  await secondTab.goto(appUrl)
  await secondTab.getByRole('heading', { name: '#general', exact: true }).waitFor()
  await page.getByRole('button', { name: 'amber', exact: true }).click()
  await page.getByLabel('Density', { exact: true }).selectOption('comfortable')
  await page.getByLabel('Font mode', { exact: true }).selectOption('mono')
  await page.getByLabel('CRT scanlines (optional)', { exact: true }).check()
  assert.equal(await page.locator('html').getAttribute('data-font'), 'mono')
  assert.equal(await page.locator('.crt-overlay').count(), 1)
  await page.getByRole('button', { name: 'Save settings', exact: true }).click()
  await page.getByRole('status').filter({ hasText: 'Saved' }).waitFor()
  await secondTab.waitForFunction(
    () =>
      document.documentElement.dataset.font === 'mono' &&
      document.documentElement.dataset.density === 'comfortable' &&
      document.documentElement.style.getPropertyValue('--accent-user') === '#ffb000',
  )
  await page.getByRole('button', { name: 'phosphor', exact: true }).click()
  await page.getByLabel('Density', { exact: true }).selectOption('compact')
  await page.getByLabel('Font mode', { exact: true }).selectOption('mixed')
  await page.getByLabel('CRT scanlines (optional)', { exact: true }).uncheck()
  await page.getByLabel('Theme', { exact: true }).selectOption('paper')
  await page.getByRole('button', { name: 'Save settings', exact: true }).click()
  await page.getByRole('status').filter({ hasText: 'Saved' }).waitFor()
  await waitForTheme(secondTab, 'paper')
  await command('#general')
  await page.getByRole('heading', { name: '#general', exact: true }).waitFor()
  await screenshot('workspace-paper')
  const contrast = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement)
    const luminance = (hex) => {
      const values = hex
        .trim()
        .replace('#', '')
        .match(/../g)
        .map((value) => parseInt(value, 16) / 255)
        .map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4))
      return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722
    }
    const foreground = luminance(style.getPropertyValue('--fg'))
    const background = luminance(style.getPropertyValue('--bg'))
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  })
  assert.ok(contrast >= 4.5)
  await command('toggle theme')
  await waitForTheme(page, 'dark')
  await page.keyboard.press('?')
  await page.getByRole('heading', { name: 'keyboard shortcuts', exact: true }).waitFor()
  await page.keyboard.press('Escape')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await navigate('# general')
  await page.waitForFunction(
    () => document.querySelector('.sidebar').getBoundingClientRect().right <= 0,
  )
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
  await screenshot('mobile')
  assert.deepEqual(errors, [])
  console.log('settings, socket broadcasts across tabs, paper contrast, shortcuts, mobile: passed')
  console.log('Browser smoke passed. Nine screenshots saved in frontend/.artifacts.')
} finally {
  await context?.close()
  await Promise.all(
    processes.map(
      (child) =>
        new Promise((resolve) => {
          if (child.exitCode !== null) return resolve()
          child.once('exit', resolve)
          child.kill()
        }),
    ),
  )
  for (const target of [temporary, profile, database]) {
    assert.ok(path.resolve(target).startsWith(`${artifacts}${path.sep}`))
    await rm(target, { force: true, recursive: true, maxRetries: 10, retryDelay: 100 })
  }
}
