// Actual deployed UI/API checks. No interception, mocks or session credentials
// appear in the receipt. Run separately from isolated CI frontend tests.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { writeFile } from 'node:fs/promises'

const url = 'https://hanoi-land-law.pages.dev'
const checks = {}
const errors = []
const browser = await chromium.launch({ headless: true })
try {
  for (const [name, viewport] of Object.entries({desktop:{width:1440,height:1000},mobile:{width:390,height:844}})) {
    const context = await browser.newContext({viewport})
    const page = await context.newPage()
    page.on('pageerror', error => errors.push({viewport:name,message:error.message}))
    await page.goto(url,{waitUntil:'networkidle',timeout:180000})
    await page.getByRole('note').filter({hasText:'Nguyên mẫu học thuật — chưa được thẩm định pháp lý độc lập.'}).waitFor({timeout:180000})
    checks[`${name}_explicit_technical_label`] = true
    checks[`${name}_no_horizontal_overflow`] = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    await page.screenshot({path:`reports/ui-live-${name}.png`,fullPage:true})
    await page.getByRole('button',{name:'Thư viện văn bản',exact:true}).click()
    await page.getByText('69 tài liệu đã công bố',{exact:true}).waitFor()
    checks[`${name}_69_documents`] = true
    await page.getByRole('button',{name:'Dự án trọng điểm',exact:true}).click()
    checks[`${name}_three_project_profiles`] = await page.locator('.project-grid article').count() === 3
    checks[`${name}_five_sources_each_project`] = await page.getByText(/5 nguồn đã công bố/).count() === 3
    await page.getByRole('button',{name:'Đánh giá hệ thống',exact:true}).click()
    checks[`${name}_evaluation_visible`] = await page.getByRole('heading',{name:'Chất lượng được đo.'}).isVisible()
    if (name === 'desktop') {
      await page.getByRole('button',{name:'Hỏi đáp pháp luật',exact:true}).click()
      await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2026-10-12')
      await page.getByLabel('Câu hỏi pháp luật').fill('Quyết định 56/2024/QĐ-UBND Hà Nội còn hiệu lực ngày 12/10/2026 không, văn bản nào thay thế?')
      await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
      await page.locator('.message.assistant').waitFor({timeout:180000})
      const text = await page.locator('.message.assistant .message-body').innerText()
      checks['desktop_real_source_fact_answer'] = text.includes('40/2026') && text.includes('02/04/2026')
      await page.locator('.citations button').first().click()
      const source = page.getByRole('dialog',{name:'Chi tiết nguồn'})
      await source.waitFor()
      checks['desktop_source_excerpt'] = (await source.innerText()).includes('Điều 2')
      checks['desktop_official_source_link'] = (await source.getByRole('link',{name:'Mở nguồn chính thức'}).getAttribute('href')).startsWith('https://congbao.hanoi.gov.vn/')
      checks['desktop_original_pdf_link'] = (await source.getByRole('link',{name:'Mở trang PDF gốc'}).getAttribute('href')).includes('#page=1')
      await page.keyboard.press('Escape')
      await page.getByRole('button',{name:/Xem quá trình kiểm chứng/}).click()
      checks['desktop_actual_trace'] = await page.getByRole('dialog',{name:'Quá trình kiểm chứng'}).locator('.trace-timeline li').count() > 0
      await page.keyboard.press('Escape')
      await page.reload({waitUntil:'networkidle'})
      await page.locator('.message.assistant').waitFor({timeout:30000})
      checks['desktop_history_restored_on_reload'] = (await page.locator('.message.assistant .message-body').innerText()).includes('40/2026')
      await page.screenshot({path:'reports/ui-live-desktop-chat.png',fullPage:true})
    }
    await context.close()
  }
  checks['no_browser_runtime_errors'] = errors.length === 0
  const report={checked_at:new Date().toISOString(),url,passed:Object.values(checks).every(Boolean),checks,errors,
    interception_used:false,acceptance_passed:false,scope:'Actual Pages/Render desktop and mobile navigation, one source-proven live answer, citations, trace and restored history.'}
  await writeFile('reports/live-ui.json',JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify(report))
  if (!report.passed) process.exitCode=1
} finally { await browser.close() }
