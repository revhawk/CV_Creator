#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

import requests
from openai import OpenAI
from dotenv import load_dotenv


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"Error reading {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def fetch_job_spec(url: str, timeout: int = 20) -> str:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        print(f"Error fetching job spec from URL: {exc}", file=sys.stderr)
        sys.exit(2)


def load_api_key(explicit_key: str | None, key_file: Path | None) -> str:
    if explicit_key:
        return explicit_key
    if key_file and key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key
    print("OpenAI API key not provided. Set OPENAI_API_KEY, use --api-key, or --api-key-file.", file=sys.stderr)
    sys.exit(3)


def build_prompt(template: str, job_spec: str, cv_md: str) -> str:
    # Fill the template placeholders with inputs if it contains the markers; otherwise append sections.
    if "===== INPUT A: JOB_SPEC =====" in template and "===== INPUT B: CV_MD =====" in template:
        return template.replace("[PASTE FULL JOB SPEC OR RECRUITER EMAIL HERE]", job_spec).replace("[PASTE YOUR MARKDOWN CV HERE]", cv_md)
    # Fallback: append sections clearly
    return f"{template}\n\n===== INPUT A: JOB_SPEC =====\n{job_spec}\n===== END INPUT A =====\n\n===== INPUT B: CV_MD =====\n{cv_md}\n===== END INPUT B =====\n"


def call_openai(prompt: str, model: str) -> str:
    client = OpenAI()
    # Use Responses API for text generation (chat-completions compatible)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a careful assistant that outputs STRICT JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    content = response.choices[0].message.content
    if not content:
        print("Empty response from OpenAI", file=sys.stderr)
        sys.exit(4)
    return content.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor CV JSON using OpenAI and a structured prompt")
    parser.add_argument("job_url", help="URL to fetch the job description text from")
    parser.add_argument("--prompt", default=str(Path("Prompt_Template.mkd")), help="Path to the base prompt template")
    parser.add_argument("--cv", default=str(Path("fullcv.mkd")), help="Path to your Markdown CV")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument("--api-key", dest="api_key", default=None, help="OpenAI API key (overrides env)")
    parser.add_argument("--api-key-file", dest="api_key_file", default=None, help="Path to file containing OpenAI API key")
    parser.add_argument("--out", default=str(Path("tailored_resume.json")), help="Where to write the JSON output")
    args = parser.parse_args()

    # Match your existing pattern: load .env if present
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    template = read_text(Path(args.prompt))
    cv_md = read_text(Path(args.cv))
    job_spec = fetch_job_spec(args.job_url)

    # Ensure API key is available to the SDK
    key = load_api_key(args.api_key, Path(args.api_key_file) if args.api_key_file else None)
    os.environ["OPENAI_API_KEY"] = key

    prompt = build_prompt(template, job_spec, cv_md)
    output_text = call_openai(prompt, args.model)

    # Try to validate JSON
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        # Attempt simple fix by trimming code fences if present
        cleaned = output_text.strip().strip("`")
        try:
            parsed = json.loads(cleaned)
        except Exception as exc:
            print("Model did not return valid JSON. Raw output:\n", output_text, file=sys.stderr)
            sys.exit(5)

    Path(args.out).write_text(json.dumps(parsed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()


