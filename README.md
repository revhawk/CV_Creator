# CV Creator

Tooling to tailor a Markdown CV to a target job spec using OpenAI, then render a DOCX via a Jinja-enabled Word template.

## Overview
- `tailor_cv.py`: reads `Prompt_Template.mkd`, fetches a job description from a URL, injects your CV from `fullcv.mkd`, calls OpenAI, and writes `tailored_resume.json`.
- `generate.py`: renders `resume_data.json` into `CV_Template.docx` using `docxtpl` and saves a timestamped `CV_Customized_YYYYMMDD-HHMMSS.docx`.
- `Prompt.mkd` / `Prompt_Template.mkd`: prompt instructions and a fillable template.

## Setup
1) Python env
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2) OpenAI API key
- Create a `.env` file (ignored by git):
```bash
printf 'OPENAI_API_KEY=YOUR_KEY_HERE\n' > .env
```
- Or export in your shell or pass `--api-key-file`.

## Tailor the CV JSON
```bash
. .venv/bin/activate
python tailor_cv.py 'https://example.com/job-posting' \
  --model gpt-4o-mini \
  --prompt Prompt_Template.mkd \
  --cv fullcv.mkd
# Output: tailored_resume.json
```

## Render DOCX
1) Replace `resume_data.json` with the tailored output:
```bash
cp tailored_resume.json resume_data.json
```
2) Render:
```bash
python generate.py
# Output: CV_Customized_YYYYMMDD-HHMMSS.docx
```

## Notes
- Secrets: `.env` is in `.gitignore` by default.
- If a job page is behind a login or heavy HTML, paste the job text into a gist or use a readable URL.
- Template customisation: edit `CV_Template.docx` placeholders (Jinja syntax) to change layout.
