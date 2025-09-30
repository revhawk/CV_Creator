#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

import requests


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Error reading {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def fetch_url(url: str, timeout: int = 25) -> str:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        print(f"Error fetching URL: {exc}", file=sys.stderr)
        sys.exit(2)


def read_pdf_text(path: Path) -> str:
    try:
        # Prefer system pdftotext if available for layout-preserving extraction
        import shutil
        if shutil.which("pdftotext"):
            import subprocess
            out = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
            return out
        else:
            # Fallback to PyPDF if pdftotext not installed
            try:
                from pypdf import PdfReader
            except Exception:
                print("Please install 'pypdf' or install 'poppler-utils' for pdftotext.", file=sys.stderr)
                sys.exit(3)
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        print(f"Error reading PDF: {exc}", file=sys.stderr)
        sys.exit(4)


PROMPT = (
    "You are a resume data normalizer. Convert the provided LinkedIn profile text into STRICT JSON matching this schema: "
    '{"summary": string, "skills": [string,...], "work_experience": ['
    '{"job_title": string, "company": string, "location": string, "start_date": string, "end_date": string, '
    '"company_blurb": string, "responsibilities": [string,...], "achievements": [string,...]}], '
    '"early_career": [{"title": string, "company": string, "dates": string}]}. '
    "Rules: UK English; dates: Mon YYYY or Present; 3–6 responsibilities, 2–5 achievements per role; no invented facts; no code fences; no trailing commas."
)


def call_openai_to_schema(text: str, model: str) -> dict:
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Output STRICT JSON only. No markdown."},
            {"role": "user", "content": PROMPT + "\n\nLINKEDIN PROFILE TEXT:\n" + text},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    content = (resp.choices[0].message.content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to strip accidental backticks
        cleaned = content.strip().strip("`")
        return json.loads(cleaned)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update resume_data.json from a LinkedIn profile source")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--pdf", help="Path to a LinkedIn profile PDF export")
    src.add_argument("--url", help="Public URL containing your profile text")
    src.add_argument("--text", help="Path to a plain text file with your profile text")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--out", default="resume_data.json", help="Output JSON path to write")
    args = parser.parse_args()

    # Load .env for OPENAI_API_KEY if present
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set. Create .env or export it.", file=sys.stderr)
        sys.exit(5)

    if args.pdf:
        text = read_pdf_text(Path(args.pdf))
    elif args.url:
        text = fetch_url(args.url)
    else:
        text = read_text_file(Path(args.text))

    data = call_openai_to_schema(text, args.model)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()




