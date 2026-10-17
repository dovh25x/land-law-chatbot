"""Run the real browser flow, including Turnstile and IndexedDB; never retrieve server history."""
import os
import subprocess
import argparse

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='https://hanoi-land-law.pages.dev')
    args=parser.parse_args()
    result=subprocess.run(['node','scripts/verify_live_ui.mjs','--chat'],env={**os.environ,'LIVE_BASE_URL':args.base_url})
    raise SystemExit(result.returncode)
