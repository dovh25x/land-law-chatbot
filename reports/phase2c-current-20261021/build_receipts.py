"""Prepare new scoped review artifacts; never connects to a database or model."""
import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
base=Path('reports/phase2c-current-20261021');old=Path('reports/phase2b-rc-20261021')
(base/'receipts').mkdir(exist_ok=True)
release=json.loads(Path('data/staging/phase2c-current/release.json').read_text())
docs={d['id']:d for d in release['documents']};access=json.loads((base/'source-access.json').read_text())
now=datetime.now(timezone.utc).isoformat()
for p in (old/'receipts').glob('*.json'):(base/'receipts'/p.name).write_bytes(p.read_bytes())
notes={
'luat-dat-dai-2024':('95|98|108','Native original PDF part2 pages5-8,14 and official consolidated44/VBHN-VPQH pages82-85,89-90 compared. Target95/98/108 text unchanged by the listed2024-25 amending laws. Current95 is read with NQ254 Article3(10) exclusions and3(13) transition/13(3) priority. Current108 is a category list, not universal entitlement; additional support authority is read with NQ2543(12), ND49 Article11(6), Hanoi40 Article17. No current review of original111(3)/(5), prices, authority or compensation amounts. NQ36/2026 signed Articles6-9,11-12 reviewed as dependency: targeted private eligible land and agricultural living-support cases exclude its state-owned housing/unlawful construction/other resettlement branches. No historical plan is deemed automatically recalculated.'),
'qd-40-2026-hanoi':('17|21|29','Native signed PDF pages10-11 Article17,13-14 Article21,18 Article29 and scope pages1/3 read. Article17 applies to compensation-eligible agricultural land:30-70percent/non-relocation6months; same-commune project-specific denominator, no cumulative prior projects; annual provincial rice price, not a household money quote. Article21 requires eligible residential land/ownership; commune allocation differs from ward apartment form; preserve area minima/maxima and multi-household exceptions. ND49 Article11(6) authorizes provincial living-support forms/levels not below national base; ND226 adds eligible-person definition to ND88. Compare original88 with consolidated53 Article11/19 and amendment226 Article7(2a). NQ36 signed Articles6-9 do not replace these two selected rules; its July1 commencement/Article12 approved-plan transition are decisive exclusions. LuatThuDo24/35/36 preserves conditionally applicable special mechanisms, not an automatic Ring4 multiplier. Current scope only for hypothetical general-regime cases with no earlier approved plan, no partial-project policy choice, no state-owned housing/illegal construction, no claim about special multiplier, amount or plot entitlement.'),
'nd-88-2024':('11','Original Article11 compared with official consolidated53 pages12-13 and ND226 Article7(2a): full-acquisition/remaining-area and no-other-housing conditions unchanged; geographic wording is now cap xa. Any current conclusion based on affected Article11 must cite the relevant226 amendment too, enforced by existing verifier. No original Article19 or24 is approved for current dates.'),
'nq-254-2025':('3|13','All15 official image GETs match source_pages checksums; native images pages2-5 and15 visually reviewed, including Article3(3)-(14) and13. Article3(10) exclusions supplement95;3(12) province framework/commune project support;3(13a/b) approved-plan and not-approved/partial project transitions;3(3) has exceptions to before-acquisition placement;3(6) current price basis supersedes original111(3), which is NOT opened by this review. Article13(1) January1 commencement and13(3) conditional priority. No proof that Ring4 automatically receives NQ258 policies. No price or timing conclusion is part of the three target answers.'),
'nd-49-2026':('11|19','Read native official signed Articles11(1)-(8),16 and19 and compare consolidated53. Article11(6) adds88 Article19(3), province may use other living-support levels/forms but not below19(1)/(2); other11 amendments keep their distinct subject matter. Article19 distinguishes both approved decisions beforeJanuary31 from no approved plan and partially approved projects; no retrospective automatic recalculation. Article16 commencesJanuary31; no blanket repeal of88. Current support case uses Hanoi40 Article17 rather than unamended88 Article19 alone.'),
'luat-thu-do-2026':('24|35|36','Native signed Articles24,35,36 read.24(2c) authorizes Hanoi council compensation/support policy;35 startsJuly1 except designated provisions;36(1)/(4)/(6) preserves approved arrangements/accepted administrative files and conditionally continued258 mechanism. New projects are not automatically governed by258. NQ36 signed copy read: Articles6-9 cover infrastructure/illegal assets/state housing/other resettlement and Articles11-12 startJuly1 and preserve approved plans. Three target cases expressly exclude those branches; no citation entitlement is enabled for NQ36 because its signed copy found only through public school publication outside the runtime official-source allowlist. No allowlist change.'),
}
selection={}
for ident,(pattern,note) in notes.items():
 doc=docs[ident];path=base/'receipts'/(ident+'.json')
 receipt=json.loads(path.read_text()) if path.exists() else {'document_id':ident,'checksum':doc['checksum'],'status':'unchanged','evidence_urls':[doc.get('publication_url') or doc['url']],'verified_scope':[]}
 chosen={c['id']:c['checksum'] for c in doc['chunks'] if re.match(r'^Điều ('+pattern+r')(?:$| ·)',c['locator'])}
 assert chosen
 if ident=='luat-dat-dai-2024':
  c=next(c for c in doc['chunks'] if c['id']=='luat-dat-dai-2024-110-scope-4');chosen[c['id']]=c['checksum']
 # Only source-reviewed metadata is extended; previous historical windows remain byte-identical.
 receipt['verified_scope'].append({'as_of_from':'2026-10-21','as_of_to':'2026-10-22','chunk_checksums':chosen})
 receipt['checked_at']=now
 receipt['relation_review']=receipt.get('relation_review','')+'\nPhase2C current review: '+note
 receipt['review_kind']='scoped source and relationship review; not independent professional legal certification'
 receipt['review_evidence']=[r for r in access if r['id'].startswith(ident) and r.get('status')==200]
 receipt['review_note_path']=str(base/'LEGAL_REVIEW.md')
 path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 selection[ident]={'chunks':list(chosen),'review':note}
doc=docs['nd-226-2025']
chosen={c['id']:c['checksum'] for c in doc['chunks'] if '-scope-' in c['id']}
note='Native signed226 Article2(4) and Article7(2a), pages16/34-35, compared with consolidated53 Article11/19 and original retained source paragraphs. Only exact compact provision excerpts are approved; neighboring provisions are excluded, particularly Article7(4a) later partially repealed by49 Article16. No current whole-document verification.'
receipt={'document_id':doc['id'],'checksum':doc['checksum'],'checked_at':now,'status':'unchanged','evidence_urls':[doc['url']], 'relation_review':note,'verified_scope':[{'as_of_from':'2026-10-21','as_of_to':'2026-10-22','chunk_checksums':chosen}],'review_evidence':[r for r in access if r['id'].startswith('nd-226-2025') and r.get('status')==200],'review_note_path':str(base/'LEGAL_REVIEW.md')}
(base/'receipts'/'nd-226-2025.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
selection[doc['id']]={'chunks':list(chosen),'review':note}
policy=json.loads((old/'source-gate.json').read_text());policy['release_id']=release['id']
for p in (base/'receipts').glob('*.json'):
 r=json.loads(p.read_text())
 if r['status']=='unchanged' and r.get('verified_scope'):
  policy['receipts'][r['document_id']]=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
(base/'source-gate.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n')
(base/'scope-selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n')
print('Current reviewed chunks:',{k:len(v['chunks']) for k,v in selection.items()})
print('Canonical policy SHA256:',hashlib.sha256(json.dumps(policy,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
