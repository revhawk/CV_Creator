from docxtpl import DocxTemplate
from jinja2 import Environment
import json

# --- 1) Use Jinja whitespace control to reduce stray empties ---
env = Environment(
    trim_blocks=True,
    lstrip_blocks=True
)

doc = DocxTemplate("CV_Template.docx")
doc.jinja_env = env

with open("resume_data.json") as f:
    ctx = json.load(f)

doc.render(ctx)

# --- 2) Post-render cleanup: drop empty paragraphs that are NOT carrying breaks ---
from docx.oxml.ns import qn

def has_section_break(p):
    pPr = p._p.pPr
    return (pPr is not None) and (pPr.sectPr is not None)

def has_page_or_column_break(p):
    for br in p._p.xpath('.//w:br'):
        br_type = br.get(qn('w:type'))
        if br_type in ('page', 'column'):
            return True
    return False

def is_effectively_empty(p):
    return (p.text.strip() == '') and not has_section_break(p) and not has_page_or_column_break(p)

def delete_paragraph(p):
    p._element.getparent().remove(p._element)

def iter_paragraphs(obj):
    for p in getattr(obj, 'paragraphs', []):
        yield p
    for t in getattr(obj, 'tables', []):
        for row in t.rows:
            for cell in row.cells:
                yield from iter_paragraphs(cell)

docx_doc = doc.docx
for p in list(iter_paragraphs(docx_doc)):
    if is_effectively_empty(p):
        delete_paragraph(p)

# --- 3) Save with sortable timestamp (Europe/London) ---
from datetime import datetime
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    now = datetime.now(ZoneInfo("Europe/London"))
except Exception:
    # Fallback to UTC if zoneinfo isn't available
    now = datetime.utcnow()

stamp = now.strftime("%Y%m%d-%H%M%S")  # e.g., 20250811-192845
out_file = f"CV_Customized_{stamp}.docx"
doc.save(out_file)
print(f"Saved: {out_file}")
