// Read-only public diagnosis: synthetic browser history only, no session/chat/model.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const out = resolve(dirname(fileURLToPath(import.meta.url)), `history-race-${new Date().toISOString().replace(/[:.]/g, '-')}`)
await mkdir(out, { recursive: true })
const report = { started_at: new Date().toISOString(), base_url: 'https://hanoi-land-law.pages.dev',
  status: 'INCOMPLETE', synthetic_history_only: true, api_mocking: false, blocked_requests: [], timeline: [] }
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.route('**/*', route => {
    const r = route.request(), url = new URL(r.url())
    if (['api.groq.com', 'api.openai.com', 'api.anthropic.com'].includes(url.hostname)
      || (url.origin === report.base_url && url.pathname.startsWith('/api/') && !['GET', 'HEAD', 'OPTIONS'].includes(r.method()))) {
      report.blocked_requests.push({ method: r.method(), host: url.hostname, path: url.pathname })
      return route.abort()
    }
    return route.continue()
  })
  const page = await context.newPage()
  await page.goto(report.base_url, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Mở thư viện nguồn đã review' }).waitFor({ timeout: 90000 })
  await page.evaluate(() => new Promise((accept, reject) => {
    const r = indexedDB.open('landlaw-history', 1)
    r.onsuccess = () => {
      const db = r.result, tx = db.transaction('conversations', 'readwrite')
      tx.objectStore('conversations').put({ id: 'qa-race', title: 'QA_SYNTHETIC_HISTORY', created_at: Date.now(),
        updated_at: Date.now(), expires_at: Date.now() + 3600000, messages: [{ id: 'qa-saved-answer', role: 'assistant',
          content: 'QA_SYNTHETIC_OLD_ANSWER', result: { status: 'answered', content: 'QA_SYNTHETIC_OLD_ANSWER',
            citations: [{ id: 'qa-saved-cite', document_id: 'qa-unreviewed', title: 'QA_SYNTHETIC_UNREVIEWED_SOURCE',
              locator: 'QA locator', excerpt: 'QA_SYNTHETIC_UNREVIEWED_EXCERPT', applicability: 'current',
              url: 'https://example.test/qa-synthetic', checked_at: '2024-08-02' }], trace: [] } }] })
      tx.oncomplete = () => { db.close(); accept() }; tx.onerror = () => reject(Error('Local history write failed'))
    }
  }))
  const started = Date.now()
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.locator('.message.assistant').waitFor()
  const snapshot = async label => ({ label, ms_since_reload: Date.now() - started,
    assistant_text: await page.locator('.message.assistant').innerText(),
    citation_buttons: await page.locator('.citations button').count(),
    source_only_banner: await page.getByRole('note').filter({ hasText: 'chỉ tra cứu đoạn nguồn đã review' }).count(),
    input_disabled: await page.getByLabel('Câu hỏi pháp luật').isDisabled(),
    old_excerpt_visible: await page.getByText('QA_SYNTHETIC_UNREVIEWED_EXCERPT', { exact: true }).count() })
  report.timeline.push(await snapshot('history_loaded_before_metadata'))
  await page.screenshot({ path: resolve(out, 'before-metadata.png'), fullPage: true })
  if (await page.locator('.citations button').count()) {
    await page.locator('.citations button').first().click()
    await page.getByText('QA_SYNTHETIC_UNREVIEWED_EXCERPT', { exact: true }).waitFor()
    report.timeline.push(await snapshot('saved_citation_opened_without_current_review'))
    await page.screenshot({ path: resolve(out, 'unreviewed-citation-before-metadata.png'), fullPage: true })
  }
  await page.getByRole('note').filter({ hasText: 'chỉ tra cứu đoạn nguồn đã review' }).waitFor({ timeout: 90000 })
  report.timeline.push(await snapshot('source_only_metadata_arrived'))
  await page.screenshot({ path: resolve(out, 'after-metadata.png'), fullPage: true })
  report.status = report.timeline.some(t => t.citation_buttons > 0 && !t.source_only_banner)
    ? 'CONFIRMED_PRESENTATION_SAFETY_RACE' : 'RACE_NOT_REPRODUCED'
  report.source_code_root_cause = 'generation=null and lookupMode=false initially make sourceOnly=false; IndexedDB resolves before remote metadata; existing !sourceOnly guards temporarily admit old structured views/citations.'
  report.server_guard_bypassed = false
} catch (error) {
  report.status = 'INCOMPLETE'; report.error = String(error?.message || error); process.exitCode = 1
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.model_requests = 0; report.session_or_chat_posts = 0
  report.scope = 'Actual browser timing with explicitly synthetic local history, no API mocks, cloud writes or generated legal claims. This diagnoses UI presentation; it does not bypass server generation/source/citation guards.'
  await writeFile(resolve(out, 'report.json'), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ status: report.status, output: out, error: report.error || null }))
}
