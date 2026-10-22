#!/usr/bin/env python3
"""Regression: changing a canonical price must identify stale page references."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
source = ROOT / "data/services.json"
original = source.read_bytes()
try:
    data = json.loads(original)
    service = next(s for s in data["services"] if s["id"] == "mani-gel")
    previous = service["price"]
    service["price"] = previous + 277
    source.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/sync_catalog.py", "--check"], cwd=ROOT, text=True, capture_output=True)
    print("COMMAND: python3 scripts/sync_catalog.py --check (mani-gel price temporarily changed)")
    print("EXIT CODE:", result.returncode)
    print("STDOUT:\n" + result.stdout)
    print("STDERR:\n" + result.stderr)
    has_location = any(".html:" in line and line.split(".html:", 1)[1].split(":", 1)[0].isdigit() for line in result.stderr.splitlines())
    if result.returncode == 0 or not has_location:
        raise SystemExit("FAIL: missing line-numbered stale price diagnostic")
    print("PASS: changed price detected with file and line")
finally:
    source.write_bytes(original)
