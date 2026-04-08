"""
Build a PDF of CompressorIQ UI pages (print-quality, multi-page per route).

Prerequisites:
  - Frontend running (default http://127.0.0.1:3000)
  - pip install -r scripts/requirements-screenshots.txt
  - playwright install chromium

Usage:
  python scripts/capture_screenshots_pdf.py
  set BASE_URL=http://localhost:3000 python scripts/capture_screenshots_pdf.py

Output:
  CompressorIQ_User_Guide_Screenshots.pdf  (project root)
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PDF = ROOT / "CompressorIQ_User_Guide_Screenshots.pdf"
PUBLIC_PDF = ROOT / "frontend" / "public" / "CompressorIQ_User_Guide_Screenshots.pdf"

PAGES: list[tuple[str, str]] = [
    ("/", "Dashboard"),
    ("/machines", "Compressors"),
    ("/service-records", "Service Records"),
    ("/work-orders", "Work orders"),
    ("/my-work", "My work"),
    ("/notifications", "Notifications"),
    ("/workflow", "Workflows"),
    ("/upload", "Upload Data"),
]


def main() -> int:
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    try:
        from playwright.sync_api import sync_playwright
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print(
            "Missing dependencies. Run:\n"
            f"  pip install -r {ROOT / 'scripts' / 'requirements-screenshots.txt'}\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    writer = PdfWriter()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for path, label in PAGES:
            url = f"{base}{path}"
            print(f"Rendering PDF for {url} ({label}) ...")
            try:
                page.goto(url, wait_until="networkidle", timeout=120_000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f"  Warning: {e}", file=sys.stderr)

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "12mm", "right": "12mm", "bottom": "12mm", "left": "12mm"},
            )
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for pg in reader.pages:
                writer.add_page(pg)

        browser.close()

    with open(OUT_PDF, "wb") as f:
        writer.write(f)

    print(f"Wrote {OUT_PDF}")
    try:
        import shutil

        shutil.copy2(OUT_PDF, PUBLIC_PDF)
        print(f"Copied to {PUBLIC_PDF} (sidebar link)")
    except OSError as e:
        print(f"Note: could not copy to public folder: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
