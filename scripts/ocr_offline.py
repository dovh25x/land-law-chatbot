"""Produce unreviewed, page-aligned OCR outside the deployed API.

Requires the free Tesseract executable and Vietnamese trained data. Every output
stays pending until a source reviewer checks the original pages and records the
reviewed checksums in the source manifest. No provider requests or publication.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--tesseract', default='tesseract')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.quality.json').exists():
        raise SystemExit('Refusing to overwrite an existing OCR or review artifact')
    pdf = pypdfium2.PdfDocument(args.pdf)
    if not 1 <= len(pdf) <= 300:
        raise SystemExit('Expected between 1 and 300 pages')
    env = {**os.environ, 'OMP_THREAD_LIMIT': '1'}
    version = subprocess.run([args.tesseract, '--version'], capture_output=True,
                             check=True, timeout=15, env=env).stdout.decode().splitlines()[0]
    results = []
    with tempfile.TemporaryDirectory(prefix='landlaw-ocr-pages-') as temporary:
        folder = Path(temporary)
        # PDFium rendering is sequential: its shared native state is not thread safe.
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=4)
            bitmap.to_pil().save(folder / f'{index:03}.png')
            bitmap.close()
            page.close()
        def recognise(index):
            base = folder / f'{index:03}'
            subprocess.run([args.tesseract, str(base.with_suffix('.png')), str(base),
                            '-l', 'vie', '--psm', '3', 'txt', 'tsv'],
                           capture_output=True, check=True, timeout=180, env=env)
            text = base.with_suffix('.txt').read_text()
            words = [row for row in csv.DictReader(io.StringIO(base.with_suffix('.tsv').read_text()), delimiter='\t')
                     if row['text'].strip() and float(row['conf']) >= 0]
            confidence = sum(float(row['conf']) for row in words) / max(1, len(words))
            report = {'page': index + 1, 'characters': len(text), 'words': len(words),
                      'mean_word_confidence': round(confidence, 2),
                      'needs_attention': len(text.strip()) < 60 or confidence < 65,
                      'review_status': 'pending'}
            print(json.dumps(report), flush=True)
            return text, report
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(recognise, range(len(pdf))))
    pdf.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\f'.join(text for text, _ in results))
    report = {'review_status': 'pending', 'engine': version, 'language': 'vie',
              'source_pdf_sha256': hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
              'ocr_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'pages': [row for _, row in results],
              'scope': 'OCR diagnostics only; confidence does not certify legal text, dates, numbers or applicability.'}
    args.output.with_suffix('.quality.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
