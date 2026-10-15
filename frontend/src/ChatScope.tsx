import { useEffect, useRef, useState } from 'react'
import { Clock3, MapPin, SlidersHorizontal, X } from 'lucide-react'

const projectLabels: Record<string, string> = { ring4: 'Vành đai 4' }

export function ScopeControl({ compact = false, project, asOf, onProjectChange, onDateChange }: {
  compact?: boolean; project: string; asOf: string; onProjectChange: (value: string) => void; onDateChange: (value: string) => void,
}) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ left: 16, bottom: 16, maxHeight: 360 })
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null)
  const close = () => { setOpen(false); trigger.current?.focus() }
  useEffect(() => {
    if (!open) return
    const place = () => {
      const rect = trigger.current?.getBoundingClientRect()
      if (!rect) return
      const bottom = Math.min(window.innerHeight - 16, window.innerHeight - rect.top + 8)
      setPosition({ left: Math.max(16, Math.min(rect.left, window.innerWidth - 336)), bottom, maxHeight: Math.max(140, window.innerHeight - bottom - 64) })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    root.current?.querySelector('select')?.focus()
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); close() } }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true); document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [open])
  const dateLabel = asOf ? asOf.split('-').reverse().join('/') : ''
  const summary = [projectLabels[project], dateLabel].filter(Boolean).join(' · ')
  return <div className="scope-picker" ref={root}>
    <button className={`composer-tool ${summary ? 'has-scope' : ''} ${compact ? 'compact' : ''}`} ref={trigger} type="button" aria-label="Phạm vi tra cứu" title={summary || 'Chọn dự án và thời điểm'} aria-expanded={open} aria-controls="scope-options" onClick={() => setOpen(value => !value)}>
      <SlidersHorizontal size={16}/><span>{summary || 'Phạm vi'}</span>
    </button>
    {open && <div className="scope-popover" style={position} id="scope-options" role="group" aria-label="Thiết lập phạm vi tra cứu">
      <header><h2>Phạm vi tra cứu</h2><button className="icon-button" type="button" onClick={close} aria-label="Đóng phạm vi"><X size={18}/></button></header>
      <label htmlFor="project"><MapPin size={16}/>Dự án</label>
      <select id="project" value={project} onChange={e => onProjectChange(e.target.value)}><option value="">Toàn Hà Nội</option><option value="ring4">Vành đai 4</option></select>
      <label htmlFor="as-of"><Clock3 size={16}/>Thời điểm áp dụng</label>
      <input id="as-of" type="date" value={asOf} onChange={e => onDateChange(e.target.value)} aria-label="Thời điểm áp dụng, để trống là hôm nay"/>
      <p>Để trống ngày để tra cứu theo hôm nay. Phạm vi dự án chỉ hỗ trợ Vành đai 4; nguồn dự án khác trong thư viện chỉ để tham khảo.</p>
      <footer><button type="button" className="scope-reset" onClick={() => { onProjectChange(''); onDateChange('') }}>Đặt lại</button><button type="button" className="button button-primary" onClick={close}>Xong</button></footer>
    </div>}
  </div>
}
