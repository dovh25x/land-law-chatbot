// Export the actual handoff report/slides as readable standalone HTML and PDF.
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import React from '../frontend/node_modules/react/index.js'
import { renderToStaticMarkup } from '../frontend/node_modules/react-dom/server.node.js'
import ReactMarkdown from '../frontend/node_modules/react-markdown/index.js'

const architecture = () => React.createElement('div', { className: 'architecture' },
  ['Nguồn chính thức → parse → E5 trên Colab', 'Supabase · PostgreSQL / pgvector',
   'React → FastAPI → LangGraph', 'Truy xuất → Groq GPT-OSS 20B → kiểm tra', 'Câu trả lời SSE · nguồn dẫn · agent trace']
    .map((label, i) => React.createElement('div', { key: i }, label)))
const markdown = text => renderToStaticMarkup(React.createElement(ReactMarkdown, {
  children: text,
  components: { code: ({ className, children }) => className === 'language-mermaid'
    ? architecture() : React.createElement('code', { className }, children) },
}))
// Small GFM table extension for our own Markdown files; never accepts remote HTML.
function render(text) {
  const lines = text.split('\n'), blocks = []
  let prose = []
  const flush = () => { if (prose.length) blocks.push(markdown(prose.join('\n'))); prose = [] }
  const cells = row => row.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(s => s.trim())
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim().startsWith('|') && /^\s*\|[\s:|\-]+\|\s*$/.test(lines[i + 1] || '')) {
      flush()
      const headers = cells(lines[i]); i += 2
      const rows = []
      while (i < lines.length && lines[i].trim().startsWith('|')) { rows.push(cells(lines[i])); i++ }
      i--
      blocks.push('<table><thead><tr>' + headers.map(c => '<th>' + markdown(c) + '</th>').join('') + '</tr></thead><tbody>'
        + rows.map(row => '<tr>' + row.map(c => '<td>' + markdown(c) + '</td>').join('') + '</tr>').join('') + '</tbody></table>')
    } else prose.push(lines[i])
  }
  flush()
  return blocks.join('\n')
}
const browser = await chromium.launch({ headless: true })
try {
  for (const [source, name, slides] of [['docs/submission/REPORT.md', 'report', false], ['docs/submission/SLIDES.md', 'slides', true]]) {
    let text = await readFile(source, 'utf8')
    if (!slides) text += '\n\n' + await readFile('reports/submission/results.md', 'utf8')
    const parts = slides ? text.split(/^## /m).slice(1).map(s => '## ' + s) : [text]
    const body = parts.map(part => '<section>' + render(part) + '</section>').join('\n')
    const html = `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hanoi Land Law — ${name}</title><style>
body{font:15px/1.7 Arial,sans-serif;color:#18343d;margin:32px auto;max-width:1040px;padding:24px;background:#fff}h1,h2,h3{line-height:1.35;color:#087f78;break-after:avoid}h1{font-size:30px}h2{font-size:23px;margin-top:30px}p,li{overflow-wrap:anywhere}a{color:#087f78}code{font-size:.85em;background:#f1f5f5;padding:2px 4px;border-radius:4px;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#f7f9fa;padding:16px;border-radius:12px}pre:has(.architecture){padding:0;background:none}table{width:100%;border-collapse:collapse;margin:20px 0;font-size:12px}th,td{padding:9px 10px;text-align:left;border:1px solid #dfe7ea;vertical-align:top}th{background:#e8f5f2}td p,th p{margin:0}tr{break-inside:avoid}thead{display:table-header-group}.architecture{display:flex;flex-direction:column;gap:8px;padding:16px;background:#f7f9fa;border-radius:14px;font:14px/1.6 Arial,sans-serif}.architecture>div{padding:12px;border:1px solid #dfe7ea;border-radius:8px;background:white;text-align:center}section{margin-bottom:30px}
${slides ? 'section{break-after:page;height:165mm;box-sizing:border-box;font-size:21px;padding:8mm 4mm}section h2{font-size:34px;margin:0 0 25px}section p{max-width:930px}section:last-child{break-after:auto}' : 'li{margin-bottom:6px}h2{border-bottom:1px solid #dfe7ea;padding-bottom:8px}'}
@media print{body{margin:0;padding:0;max-width:none}section{margin:0}a{text-decoration:none}}
</style></head><body>${body}</body></html>`
    await writeFile(`docs/submission/${name}.html`, html)
    const page = await browser.newPage()
    await page.setContent(html)
    await page.pdf({ path: `docs/submission/${name}.pdf`, format: 'A4', landscape: slides,
      printBackground: true, margin: { top: '15mm', bottom: '15mm', left: '15mm', right: '15mm' } })
    await page.close()
  }
} finally { await browser.close() }
console.log('Exported report and 10-slide HTML/PDF from current Markdown and actual results.')
