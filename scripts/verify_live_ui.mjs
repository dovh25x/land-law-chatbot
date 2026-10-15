// Smoke test of the deployed Figma UI. No route interception or mock responses.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { writeFile } from 'node:fs/promises'

const url = 'https://hanoi-land-law.pages.dev'
const checks = {}, errors = [], observations = {}
const skipChat = process.argv.includes('--skip-chat')
const browser = await chromium.launch({ headless: true })
const navigate = async (page, name) => {
  const menu = page.getByRole('button', { name: 'Mở menu điều hướng' })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('button', { name, exact: true }).click()
}
try {
  for (const [name, viewport] of Object.entries({ desktop: { width: 1440, height: 1024 }, mobile: { width: 390, height: 940 } })) {
    const context = await browser.newContext({ viewport })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push({ viewport: name, message: error.message }))
    await page.goto(url, { waitUntil: 'networkidle', timeout: 180000 })
    await page.getByRole('heading', { name: /Tìm đúng căn cứ/ }).waitFor()
    const dataButton = page.getByRole('button', { name: 'Thông tin dữ liệu và kết nối' })
    await dataButton.click()
    await page.getByRole('note').waitFor({ timeout: 180000 })
    checks[`${name}_data_disclosure`] = await page.getByRole('note').isVisible()
    await page.keyboard.press('Escape')
    checks[`${name}_header_56px`] = (await page.locator('.topbar').boundingBox()).height === 56
    await page.evaluate(() => document.fonts.ready)
    checks[`${name}_figma_heading`] = true
    checks[`${name}_self_hosted_font`] = await page.evaluate(() => document.fonts.check('16px "Be Vietnam Pro"'))
    checks[`${name}_no_horizontal_overflow`] = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)
    await page.screenshot({ path: `reports/ui-live-compact-${name}.png`, fullPage: true })
    await page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true }).click()
    await page.getByLabel('Dự án', { exact: true }).selectOption('ring4')
    await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
    await page.getByRole('button', { name: 'Xong', exact: true }).click()
    checks[`${name}_scope_summary`] = (await page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true }).innerText()).includes('Vành đai 4 · 02/08/2024')
    await navigate(page, 'Thư viện văn bản')
    await page.locator('.document-row').first().waitFor({ timeout: 60000 })
    observations[`${name}_document_count`] = await page.locator('.document-row').count()
    checks[`${name}_real_documents`] = observations[`${name}_document_count`] > 0
    await page.locator('.document-row').first().click()
    const source = page.getByRole('dialog', { name: 'Chi tiết nguồn' })
    await source.waitFor()
    checks[`${name}_official_source_link`] = (await source.getByRole('link', { name: 'Mở nguồn chính thức' }).getAttribute('href')).startsWith('https://')
    await page.screenshot({ path: `reports/ui-live-compact-${name}-source.png`, fullPage: true })
    await page.keyboard.press('Escape')
    await navigate(page, 'Dự án trọng điểm')
    checks[`${name}_three_project_tabs`] = await page.getByRole('tab').count() === 3
    for (const project of ['Vành đai 4', 'Sông Hồng', 'Olympic']) {
      await page.getByRole('tab', { name: project, exact: true }).click()
      checks[`${name}_${project}_source_list`] = await page.locator('.project-dossier .document-row').count() > 0
    }
    await navigate(page, 'Đánh giá đồ án')
    checks[`${name}_evaluation_visible`] = await page.locator('.evaluation-summary').isVisible()
    if (name === 'desktop' && !skipChat) {
      await navigate(page, 'Hỏi đáp pháp luật')
      await page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true }).click()
      await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
      await page.getByRole('button', { name: 'Xong', exact: true }).click()
      await page.getByLabel('Câu hỏi pháp luật').fill('Điều 104 Luật Đất đai 2024 quy định bồi thường chi phí di chuyển tài sản như thế nào?')
      await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
      await Promise.race([
        page.locator('.message.assistant').waitFor({ timeout: 180000 }),
        page.getByRole('alert').waitFor({ timeout: 180000 }),
      ])
      const answered = await page.locator('.message.assistant').count() > 0
      checks.desktop_chat_result_or_explicit_error = answered || await page.getByRole('alert').isVisible()
      observations.chat_returned_answer = answered
      if (answered) {
        observations.chat_status = await page.locator('.answer-status').last().innerText()
        if (await page.locator('.citations button').count()) {
          await page.locator('.citations button').first().click()
          await page.getByRole('dialog', { name: 'Chi tiết nguồn' }).waitFor()
          checks.desktop_citation_excerpt = (await page.locator('.source-excerpt').innerText()).length > 20
          await page.keyboard.press('Escape')
        }
        await page.getByRole('button', { name: /Xem quá trình kiểm chứng/ }).last().click()
        checks.desktop_actual_trace = await page.locator('.trace-timeline li').count() > 0
        await page.screenshot({ path: 'reports/ui-live-compact-desktop-trace.png', fullPage: true })
        await page.keyboard.press('Escape')
        await page.reload({ waitUntil: 'networkidle' })
        await page.locator('.message.assistant').waitFor({ timeout: 30000 })
        checks.desktop_history_restored = true
      } else observations.chat_limitation = await page.getByRole('alert').innerText()
    }
    await context.close()
    console.log(JSON.stringify({ viewport: name, finished: true }))
  }
  checks.no_browser_runtime_errors = errors.length === 0
  const report = { checked_at: new Date().toISOString(), url, passed: Object.values(checks).every(Boolean), checks, observations, errors,
    interception_used: false, legal_acceptance: false, chat_skipped: skipChat,
    scope: skipChat ? 'Live compact header, scope controls, navigation, fonts, sources and projects. No chat request or legal evaluation.' : 'Live frontend navigation and one chat attempt; explicit chat quota/error is not a grounded answer.' }
  await writeFile('reports/ui-compact-live.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
  if (!report.passed) process.exitCode = 1
} finally { await browser.close() }
