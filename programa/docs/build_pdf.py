"""Sugeneruoja Dokumentacija.pdf (pagrindiniame aplanke) iš docs/dokumentacija.html per Microsoft Edge.

Paleidimas:  .venv\\Scripts\\python docs\\build_pdf.py
"""
import os
import subprocess
from pathlib import Path

DOCS = Path(__file__).resolve().parent
OUT = DOCS.parent.parent / "Dokumentacija.pdf"
EDGE = next(p for p in (Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
                        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe") if p.exists())

subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                f"--print-to-pdf={OUT}", (DOCS / "dokumentacija.html").as_uri()], check=True, timeout=120)
print(f"Sukurta: {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
