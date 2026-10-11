"""Fail when any locally configured secret accidentally appears in tracked candidate outputs."""
from pathlib import Path
from dotenv import dotenv_values

values = dotenv_values(".env")
secrets = [v for k, v in values.items() if v and len(v) > 12 and any(x in k for x in ("KEY", "TOKEN", "SECRET", "DATABASE_URL"))]
paths = [p for folder in ("backend", "frontend/dist", "docs", "reports") for p in Path(folder).rglob("*")
         if p.is_file() and p.suffix in {".py", ".js", ".html", ".json", ".md", ".css"}]
leaked = [str(p) for p in paths if any(s in p.read_text(errors="ignore") for s in secrets)]
if leaked:
    raise SystemExit("Secret present in outputs: " + ", ".join(leaked))
print("No configured secret found in source, frontend bundle or reports.")
