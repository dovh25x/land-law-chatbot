// Unmocked public source-only browser QA. Run ONLY after release-owner confirms deployment.
// No chat/session POST, model call, challenge automation, or existing user history.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

if (!process.argv.includes('--deployed-confirmed')) throw Error('Wait for the release owner deployment signal; add --deployed-confirmed only then.')
const base = 'https://hanoi-land-law.pages.dev'
const expectedFP = '8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464'
const expectedCorpus = 'corpus-1afca764aa6692e0'
const expectedCommit = 'ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec'
const directory = resolve(dirname(fileURLToPath(import.meta.url)), `public-source-${new Date().toISOString().replace(/[:.]/g, '-')}`)
await mkdir(directory, { recursive: true })
let browser
const report = { started_at: new Date().toISOString(), base_url: base, status: 'INCOMPLETE',
  runtime_fingerprint_expected: expectedFP, corpus_expected: expectedCorpus,
  source_commit_expected: expectedCommit,
  no_api_mocking: true, prohibited_requests: [], external_non_get_requests: [], api_results: [], browser_checks: [], ui_date_filters: [],
  chat: 'NOT TESTED — disabled in source-only mode', follow_up: 'NOT TESTED — no generated conversation',
  human_turnstile: 'NOT TESTED — no challenge automation or session creation',
  latency_scope: 'Observed source GET/browser timings only, not model latency', model_requests: 0 }

const ensure = (condition, reason) => { if (!condition) throw Error(reason) }
async function get(page, path) {
  const start = Date.now(), response = await page.request.get(base + path, { timeout: 90000 })
  ensure(response.ok(), `Public GET ${path} HTTP${response.status()}`)
  report.api_results.push({ path, http_status: response.status(), elapsed_ms: Date.now() - start })
  return response.json()
}
async function openMenu(page) {
  const opener = page.getByRole('button', { name: 'Mở menu điều hướng' })
  if (await opener.isVisible()) await opener.click()
}
async function setDay(page, day) {
  const selected = await page.getByLabel('Thời điểm áp dụng nguồn').inputValue()
  if (selected === day) {
    // Initial controlled value comes from server review date while lookupDate
    // remains empty; filling an identical value need not dispatch React change.
    const note = await page.getByRole('note').filter({ hasText: 'chỉ tra cứu đoạn nguồn đã review' }).innerText()
    ensure(note.includes(new Date(day).toLocaleDateString('vi-VN')), 'Selected day differs from displayed review date')
    report.ui_date_filters.push({ as_of: day, outcome: 'ALREADY_SELECTED_AND_DISPLAYED_NO_REDUNDANT_REQUEST' })
    return
  }
  await page.getByLabel('Thời điểm áp dụng nguồn').fill(day)
  const response = page.waitForResponse(r => r.url().endsWith(`/api/v1/documents?as_of=${day}`) && r.request().method() === 'GET')
  await page.getByRole('button', { name: 'Đối chiếu ngày đã chọn' }).click()
  ensure((await response).ok(), 'Date-filter request failed')
  report.ui_date_filters.push({ as_of: day, outcome: 'CHANGED_AND_PUBLIC_GET_SUCCEEDED' })
}

try {
  browser = await chromium.launch({ headless: true })
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, isMobile: width < 768,
      hasTouch: width < 768, deviceScaleFactor: width < 768 ? 2 : 1 })
    // Block application writes/model hosts; ordinary external challenge telemetry
    // may load naturally. It never proves human Turnstile completion.
    await context.route('**/*', route => {
      const request = route.request()
      const url = new URL(request.url())
      const modelHost = ['api.groq.com', 'api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com'].includes(url.hostname)
      const ownHost = url.origin === base || url.hostname.endsWith('.onrender.com')
      const ownAPI = ownHost && url.pathname.startsWith('/api/')
      const nonReadMethod = !['GET', 'HEAD', 'OPTIONS'].includes(request.method())
      if (modelHost || (ownAPI && nonReadMethod)) {
        report.prohibited_requests.push({ method: request.method(), host: url.hostname, path: url.pathname })
        return route.abort('blockedbyclient')
      }
      const externalPath = url.hostname === 'challenges.cloudflare.com' ? '/cdn-cgi/challenge-platform/[opaque-path-omitted]' : url.pathname
      if (nonReadMethod) report.external_non_get_requests.push({ method: request.method(), host: url.hostname, path: externalPath,
        classification: 'Normal page/external telemetry only; not an application API write or human challenge success' })
      return route.continue()
    })
    const page = await context.newPage()
    const check = { width, mode: width < 768 ? 'emulated_mobile' : 'desktop_browser', physical_device: false,
      status: 'INCOMPLETE', cases: [], stage: 'initial_load' }
    report.browser_checks.push(check)
    await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 90000 })
    await page.getByRole('button', { name: 'Mở thư viện nguồn đã review' }).waitFor({ timeout: 90000 })
    ensure(await page.getByLabel('Câu hỏi pháp luật').isDisabled(), 'Chat must be disabled')
    const ready = await get(page, '/readyz'), status = await get(page, '/api/v1/status')
    ensure(ready.configuration_sha256 === expectedFP, 'Deployed runtime fingerprint mismatch')
    ensure(ready.storage === 'postgresql' && ready.database === true, 'Expected healthy PostgreSQL')
    ensure(ready.corpus_release === expectedCorpus, 'Deployed corpus mismatch')
    ensure(status.source_lookup_only === true && status.generation_available === false, 'Source-only capability mismatch')
    check.frontend_script_urls = await page.locator('script[src]').evaluateAll(nodes => nodes.map(node => node.src))
    const integrity = JSON.parse(await readFile(resolve(dirname(fileURLToPath(import.meta.url)), '../public-frontend-integrity-final.json'), 'utf8'))
    ensure(integrity.status === 'PASS' && integrity.source_sha === expectedCommit, 'Expected production build identity missing')
    const resources = await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(node => node.src || node.href))
    check.frontend_assets = []
    for (const asset of integrity.production_assets) {
      ensure(resources.includes(base + asset.path), 'Page loaded a different frontend bundle')
      const response = await page.request.get(base + asset.path)
      ensure(response.ok(), 'Frontend asset download failed')
      const hash = createHash('sha256').update(await response.body()).digest('hex')
      ensure(hash === asset.sha256, 'Frontend asset differs from final ec5 production build')
      check.frontend_assets.push({ path: asset.path, sha256: hash, matches_final_production_build: true })
    }
    check.runtime_fingerprint = ready.configuration_sha256
    check.corpus_id = ready.corpus_release
    const caseResults = []
    for (const [day, expected] of [['2026-10-21', 43], ['2026-10-22', 1], ['2024-08-02', 25]]) {
      const listed = await get(page, `/api/v1/documents?as_of=${day}`)
      ensure(listed.source_lookup_only === true && listed.as_of === day && listed.references.length === 0, 'Unreviewed catalog/reference admission')
      ensure(listed.verified_passage_count === expected, `Wrong passage count at${day}`)
      let count = 0
      for (const document of listed.documents) {
        const detail = await get(page, `/api/v1/documents/${encodeURIComponent(document.id)}?as_of=${day}`)
        ensure(detail.whole_document_verified === false && detail.relations.length === 0, 'Whole-document validation overclaim')
        ensure(detail.document.review_as_of === day && detail.document.applicability_verified === false, 'Wrong review date/whole-document applicability')
        for (const chunk of detail.document.chunks) {
          ensure(createHash('sha256').update(chunk.text).digest('hex') === chunk.checksum, 'Excerpt checksum mismatch')
          ensure(!('embedding' in chunk), 'Embeddings exposed')
          count++
        }
      }
      ensure(count === expected, 'List/detail count mismatch')
      caseResults.push({ as_of: day, documents: listed.documents.length, passages: count, excerpt_checksums: 'PASS' })
      check.cases = caseResults
    }
    check.stage = 'source_panel'
    await page.getByRole('button', { name: 'Mở thư viện nguồn đã review' }).click()
    await setDay(page, '2026-10-21')
    const list = await get(page, '/api/v1/documents?as_of=2026-10-21')
    const sample = list.documents.find(d => d.id === 'qd-40-2026-hanoi') || list.documents[0]
    const row = page.locator('.document-row').filter({ hasText: sample.title }).first()
    const expectedDetail = await get(page, `/api/v1/documents/${encodeURIComponent(sample.id)}?as_of=2026-10-21`)
    await row.click()
    await page.locator('.source-card .source-excerpt').first().waitFor()
    ensure(await page.locator('.source-card .source-excerpt').count() === expectedDetail.document.chunks.length, 'Source panel omitted reviewed excerpts')
    ensure(await page.locator('.source-card').innerText().then(t => t.includes('Không phải đáp án được model kiểm chứng')), 'Missing extractive-only label')
    const technical = page.locator('.source-technical')
    await technical.locator('summary').click()
    ensure((await technical.innerText()).includes(sample.checksum), 'Source version checksum not visible')
    const official = page.getByRole('link', { name: 'Mở nguồn chính thức', exact: true })
    ensure(await official.getAttribute('href') === sample.url, 'Official source URL mismatch')
    const navigation = { initial_url: sample.url, outcome: 'INCOMPLETE', final_url: null, title: null, http_status: null }
    check.external_document_navigation = navigation
    const original = await context.newPage()
    try {
      const opened = await original.goto(sample.url, { waitUntil: 'domcontentloaded', timeout: 45000 })
      navigation.final_url = original.url()
      navigation.title = await original.title()
      navigation.http_status = opened?.status() ?? null
      navigation.outcome = opened?.ok() ? 'PASS_NAVIGATION' : 'INCOMPLETE_HTTP'
      navigation.scope = 'Actual browser navigation to the expected official source URL; not a new checksum/legal applicability review'
      if (opened?.ok()) await original.screenshot({ path: resolve(directory, `official-source-${width}.png`), fullPage: false })
    } catch (error) {
      navigation.final_url = original.url()
      navigation.title = await original.title().catch(() => null)
      navigation.error = String(error?.message || error)
      navigation.scope = 'External host blocked, unavailable, download navigation or browser timeout; href match alone is not successful open'
    } finally {
      await original.close()
    }
    await page.screenshot({ path: resolve(directory, `source-${width}.png`), fullPage: true })
    check.source_panel = 'PASS'
    check.official_link_target = 'PASS_URL_MATCH_ONLY'
    await page.keyboard.press('Escape')
    await setDay(page, '2026-10-22')
    await page.waitForFunction(() => document.querySelectorAll('.document-row').length === 1)
    ensure(await page.locator('.document-row').count() === 1, 'Next-day UI must show only the reviewed header document')
    await setDay(page, '2024-08-02')
    await page.waitForFunction(() => document.querySelectorAll('.document-row').length > 1)
    ensure(await page.locator('.document-row').count() > 0, 'Historical reviewed sources not shown')
    ensure(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow')
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByRole('note').filter({ hasText: 'chỉ tra cứu đoạn nguồn đã review' }).waitFor()
    ensure(await page.getByLabel('Câu hỏi pháp luật').isDisabled(), 'Reload re-enabled chat')
    check.stage = 'history_reload_before_metadata'
    // Synthetic, non-legal local-only history proves retention/clearing; never sent to server.
    await page.evaluate(() => new Promise((accept, reject) => {
      const request = indexedDB.open('landlaw-history', 1)
      request.onsuccess = () => {
        const db = request.result, tx = db.transaction('conversations', 'readwrite')
        tx.objectStore('conversations').put({ id: 'qa-local-only', title: 'QA_LOCAL_HISTORY_MARKER',
          created_at: Date.now(), updated_at: Date.now(), expires_at: Date.now() + 3600000,
          messages: [{ id: 'qa-local-message', role: 'assistant', content: 'QA_LOCAL_HISTORY_MARKER',
            result: { status: 'answered', content: 'QA_LOCAL_HISTORY_MARKER', citations: [{ id: 'qa-old', title: 'QA_OLD_SOURCE', excerpt: 'QA_OLD_EXCERPT' }], trace: [] } }] })
        tx.oncomplete = () => { db.close(); accept() }
        tx.onerror = () => reject(Error('Local-only history write failed'))
      }
      request.onerror = () => reject(Error('Browser IndexedDB unavailable'))
    }))
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.locator('.message.assistant').filter({ hasText: 'QA_LOCAL_HISTORY_MARKER' }).waitFor()
    ensure((await page.locator('.message.assistant').innerText()).includes('chưa được xác minh lại'), 'Saved history lacks unverified label')
    ensure(await page.getByText('QA_OLD_EXCERPT', { exact: true }).count() === 0, 'Saved citation bypassed reviewed view')
    await openMenu(page)
    await page.getByRole('button', { name: 'Xóa toàn bộ lịch sử', exact: true }).click()
    await page.getByRole('button', { name: 'Xóa lịch sử', exact: true }).click()
    await page.getByRole('button', { name: 'Xóa lịch sử', exact: true }).waitFor({ state: 'hidden' })
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: 'Mở thư viện nguồn đã review' }).waitFor()
    ensure(await page.locator('.message').count() === 0, 'Local history was not cleared')
    await page.screenshot({ path: resolve(directory, `chat-disabled-${width}.png`), fullPage: true })
    Object.assign(check, { status: 'PASS', stage: 'complete', reload: 'PASS', synthetic_local_history_label_clear: 'PASS',
      horizontal_overflow: false, chat_disabled: true })
    await context.close()
  }
  ensure(report.prohibited_requests.length === 0, 'Unexpected write/session/chat request was blocked')
  report.status = report.browser_checks.every(item => item.external_document_navigation.outcome === 'PASS_NAVIGATION')
    ? 'PASS_SOURCE_ONLY_PUBLIC_BROWSER' : 'PARTIAL_SOURCE_ONLY_PUBLIC_BROWSER'
} catch (error) {
  report.status = 'FAIL'
  report.error = String(error?.message || error)
  process.exitCode = 1
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.scope = 'Actual canonical public source-lookup browser and GET API only. No mocked success responses, chat/model/session or challenge automation; synthetic history stays in an isolated browser context. No claim of generated answer/follow-up or human Turnstile success.'
  await writeFile(resolve(directory, 'report.json'), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ status: report.status, output: directory, error: report.error || null }))
}
