// Real public checks: no intercepted API, test challenge keys or persisted conversation artifacts.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { writeFile, mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'

const chat = process.argv.includes('--chat'), sourceOnly = process.argv.includes('--source-only')
const base = process.env.LIVE_BASE_URL || 'https://hanoi-land-law.pages.dev'
const directory = process.env.LIVE_REPORT_DIR || `reports/live-${new Date().toISOString().replace(/[:.]/g, '-')}`
const output = resolve(directory, chat ? (sourceOnly ? 'source-only.json' : 'generation.json') : 'navigation.json')
const checks = []
let phase = 'configuration', browser, turnstileTokenObserved = false, turnstileSessionVerified = false, generationChecked = false
let challengeModeResolved = process.env.LIVE_SESSION_CHALLENGE_MODE || 'auto'
let turnstileScriptRequested = false
const local = spawnSync(existsSync('.venv/bin/python') ? '.venv/bin/python' : 'python3', ['-c', 'import os; from landlaw.config import Settings; from landlaw.evaluation import configuration_fingerprint; from pydantic import SecretStr; s=Settings(); s=s.model_copy(update={"database_url":SecretStr("postgresql://fingerprint-only/metadata" if os.getenv("LIVE_STORAGE_BACKEND","postgresql")=="postgresql" else "")}); print(configuration_fingerprint(s))'], { encoding: 'utf8' })
const expected = process.env.LIVE_EXPECTED_CONFIGURATION || (local.status === 0 ? local.stdout.trim() : null)
const menu = async page => {
  const opener = page.getByRole('button', { name: 'Mở menu điều hướng' })
  if (await opener.isVisible()) await opener.click()
}
const browserHistory = page => page.evaluate(() => new Promise((accept, reject) => {
  const request = indexedDB.open('landlaw-history', 1)
  request.onsuccess = () => {
    const db = request.result, transaction = db.transaction('conversations'), query = transaction.objectStore('conversations').getAll()
    query.onsuccess = () => accept(query.result)
    query.onerror = () => reject(Error('Local history unavailable'))
    transaction.oncomplete = () => db.close()
  }
  request.onerror = () => reject(Error('IndexedDB unavailable'))
}))
const get = async (page, path) => {
  const response = await page.request.get(base + path, { timeout: 90000 })
  if (!response.ok()) throw Error(`Public metadata HTTP ${response.status()}`)
  return response.json()
}

try {
  await mkdir(directory, { recursive: true })
  browser = await chromium.launch({ headless: true })
  for (const width of [1440, 390, 320]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, isMobile: width < 768, hasTouch: width < 768, deviceScaleFactor: width < 768 ? 2 : 1 })
    const page = await context.newPage()
    page.on('request', request => { if (request.url().includes('challenges.cloudflare.com')) turnstileScriptRequested = true })
    await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 90000 })
    await page.getByLabel('Câu hỏi pháp luật').waitFor()
    await page.evaluate(() => document.fonts.ready)
    if (!expected) throw Error('Cannot establish the tested runtime fingerprint')
    const readiness = await get(page, '/readyz'), status = await get(page, '/api/v1/status'), evaluation = await get(page, '/api/v1/evaluations/latest')
    if (evaluation.active_configuration_sha256 !== expected) throw Error('Deployed fingerprint differs from tested source')
    if (process.env.LIVE_EXPECTED_CORPUS && readiness.corpus_release !== process.env.LIVE_EXPECTED_CORPUS) throw Error('Active corpus differs from selected release')
    if (!readiness.database || readiness.storage !== 'postgresql') throw Error('Expected PostgreSQL runtime')
    if (await page.getByLabel('Dự án', { exact: true }).count() || await page.getByLabel('Chế độ truy xuất').count()) throw Error('Unexpected scope/model controls')
    if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw Error('Horizontal overflow')
    phase = 'navigation'
    await menu(page); await page.getByRole('button', { name: 'Văn bản pháp luật', exact: true }).click()
    await page.locator('.document-row').first().waitFor({ timeout: 90000 })
    const { documents } = await get(page, '/api/v1/documents')
    if (!documents.length || documents.some(doc => doc.project && doc.project !== 'ring4')) throw Error('Unexpected corpus scope')
    await page.locator('.document-row').first().click()
    const source = page.locator('[aria-label="Nguồn căn cứ"]')
    await source.waitFor()
    if (width >= 1280 && await source.getAttribute('role') !== 'complementary') throw Error('Desktop source is not a comparison region')
    if (width < 1280 && await source.getAttribute('role') !== 'dialog') throw Error('Mobile source is not modal')
    await page.keyboard.press('Escape')
    await menu(page); await page.getByRole('button', { name: 'Hỏi đáp', exact: true }).click()
    await page.screenshot({ path: resolve(directory, `navigation-${width}.png`), fullPage: true })
    checks.push({ width, device_mode: width < 768 ? 'emulated_mobile' : 'desktop_browser', physical_device: false, corpus_documents: documents.length, corpus_release: readiness.corpus_release, runtime_configuration_sha256: evaluation.active_configuration_sha256, report_matches_configuration: evaluation.matches_active_configuration, report_matches_corpus: evaluation.matches_active_release, responsive: true, source_access: true })
    if (width === 1440 && chat) {
      if (!status.generation_available) throw Error(`Generation unavailable: ${status.reason || 'unknown'}`)
      challengeModeResolved = process.env.LIVE_SESSION_CHALLENGE_MODE || status.session_challenge_mode || 'auto'
      if (challengeModeResolved === 'turnstile') {
        phase = 'turnstile'
        // Managed interactive challenges require the human user. Never automate the checkbox.
        await page.waitForFunction(() => !!document.querySelector('input[name="cf-turnstile-response"]')?.value, {}, { timeout: 45000 })
        turnstileTokenObserved = true
      } else if (challengeModeResolved === 'auto') {
        phase = 'turnstile_or_disabled'
        // Older backends do not expose the mode. A rendered widget means the
        // challenge is active; otherwise proceed as the demo disabled mode.
        try {
          await page.waitForFunction(() => !!document.querySelector('input[name="cf-turnstile-response"]')?.value, {}, { timeout: 6000 })
          turnstileTokenObserved = true
          challengeModeResolved = 'turnstile'
        } catch { challengeModeResolved = 'disabled' }
      } else if (challengeModeResolved !== 'disabled') {
        throw Error(`Unknown LIVE_SESSION_CHALLENGE_MODE: ${challengeModeResolved}`)
      }
      const sessionResponse = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/sessions'), { timeout: 110000 })
      async function submit(question) {
        const previous = await page.locator('.message.assistant').count()
        const pending = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/v1/chat'), { timeout: 110000 })
        await page.getByLabel('Câu hỏi pháp luật').fill(question)
        await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
        const response = await pending
        if (!response.ok()) throw Error(`Chat HTTP ${response.status()}`)
        await page.locator('.message.assistant').nth(previous).waitFor({ timeout: 110000 })
        for (let attempt = 0; attempt < 60; attempt++) {
          const rows = await browserHistory(page), latest = rows.sort((a, b) => b.updated_at - a.updated_at)[0]
          const answers = latest?.messages.filter(message => message.role === 'assistant') || []
          if (answers.length > previous) {
            const result = answers.at(-1)?.result
            if (!result || result.status !== 'answered' || !result.citations.length) throw Error('No completed source-backed answer')
            return { result, payload: response.request().postDataJSON() }
          }
          await page.waitForTimeout(50)
        }
        throw Error('Result was not saved in browser history')
      }
      phase = 'generation'
      const first = await submit(sourceOnly ? 'Quyết định 56/2024/QĐ-UBND Hà Nội còn hiệu lực không? Văn bản nào thay thế?' : 'Khi Nhà nước thu hồi đất nông nghiệp, người dân có thể nhận những khoản hỗ trợ nào?')
      const verified = await sessionResponse
      if (verified.status() !== 201) throw Error(`Session HTTP ${verified.status()}`)
      turnstileSessionVerified = turnstileTokenObserved
      if (challengeModeResolved === 'disabled' && turnstileScriptRequested) throw Error('Turnstile script loaded while challenge is disabled')
      if (first.result.model !== 'openai/gpt-oss-120b' || (sourceOnly ? first.result.llm_calls !== 0 : first.result.llm_calls < 1)) throw Error('Unexpected model/generation origin')
      generationChecked = !sourceOnly
      await page.locator('.message.assistant .citations button').first().click(); await source.waitFor(); await page.keyboard.press('Escape')
      phase = 'follow_up'
      const second = await submit('Vậy mức hỗ trợ ổn định đời sống cho một nhân khẩu được tính như thế nào khi đất nông nghiệp bị thu hồi?')
      if (second.payload.history.length < 2 || second.payload.session_id !== first.payload.session_id) throw Error('Follow-up context/session missing')
      const session = await page.evaluate(() => JSON.parse(sessionStorage.getItem('landlaw-session')))
      const forbidden = await page.request.get(base + '/api/v1/sessions/' + session.session_id, { headers: { Authorization: 'Bearer invalid' } })
      if (forbidden.status() !== 404) throw Error('Session isolation failed')
      const retired = await page.request.get(base + '/api/v1/sessions/' + session.session_id + '/messages', { headers: { Authorization: 'Bearer ' + session.token } })
      if (retired.status() !== 410) throw Error('Server history endpoint not retired')
      phase = 'reload_and_delete'; await page.reload(); await page.locator('.message.assistant').nth(1).waitFor()
      await menu(page); await page.getByRole('button', { name: 'Xóa toàn bộ lịch sử' }).click()
      await page.getByRole('dialog').getByRole('button', { name: 'Xóa lịch sử', exact: true }).click()
      await page.waitForFunction(() => document.querySelectorAll('.history-row').length === 0)
      if ((await browserHistory(page)).length) throw Error('Local history not cleared')
      checks.push({ llm_generation_checked: !sourceOnly, model: first.result.model, first_llm_calls: first.result.llm_calls, follow_up_llm_calls: second.result.llm_calls, follow_up_history_pairs: second.payload.history.length / 2, client_sources: true, reload: true, delete: true, server_history_410: true, session_isolation: true })
    }
    await context.close()
  }
  await writeFile(output, JSON.stringify({ passed: true, checked_at: new Date().toISOString(), base_url: base, session_challenge_mode: challengeModeResolved, llm_generation_checked: generationChecked, turnstile_token_observed: turnstileTokenObserved, turnstile_script_requested: turnstileScriptRequested, turnstile_browser_checked: turnstileSessionVerified, physical_device: false, checks }, null, 2) + '\n')
  console.log(JSON.stringify({ passed: true, output, session_challenge_mode: challengeModeResolved, llm_generation_checked: generationChecked }))
} catch (error) {
  const safeError = phase === 'turnstile' ? 'Managed Turnstile did not produce a token; human interaction may be required.' : error.message
  await mkdir(directory, { recursive: true })
  await writeFile(output, JSON.stringify({ passed: false, checked_at: new Date().toISOString(), base_url: base, phase, error: safeError, session_challenge_mode: challengeModeResolved, llm_generation_checked: generationChecked, turnstile_token_observed: turnstileTokenObserved, turnstile_script_requested: turnstileScriptRequested, turnstile_browser_checked: turnstileSessionVerified, physical_device: false, checks }, null, 2) + '\n')
  console.log(JSON.stringify({ passed: false, phase, error: safeError, output })); process.exitCode = 1
} finally { await browser?.close() }
