"""Build the Word manuscript for the AAS submission system from the Markdown draft.
usage (repo root): uv run --with python-docx python docs/papers/rnaas_allwise/build_docx.py"""
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

D = "docs/papers/rnaas_allwise/"
src = open("docs/papers/RNAAS_AllWISE_profile_fit_draft.md").read().split("\n", 1)[1]  # drop the DRAFT line
doc = Document()
doc.styles["Normal"].font.name = "Times New Roman"
doc.styles["Normal"].font.size = Pt(12)


def para(text, bold=False, align=None, italic=False):
    p = doc.add_paragraph()
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            r = p.add_run(part)
            r.bold = bold or i % 2 == 1
            r.italic = italic
    if align:
        p.alignment = align
    return p


blocks = [" ".join(b.split()) for b in re.split(r"\n\s*\n", src) if b.strip()]
refs = False
for b in blocks:
    if b.startswith("**") and b.endswith("**") and "Figure 1." not in b:
        para(b.strip("*"), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)  # title
    elif b.startswith("Alan Shortz") or b.startswith("¹"):
        para(b, align=WD_ALIGN_PARAGRAPH.CENTER)
    elif b.startswith("## "):
        refs = b == "## References"
        para(b[3:].upper() if b[3:] in ("Abstract", "Acknowledgments", "References") else b[3:], bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER if b[3:] == "Abstract" else None)
    elif b.startswith("**Figure 1.**"):
        doc.add_picture(D + "figure1.png", width=Inches(6.5))
        para(b)
    else:
        para(b)
if refs:  # the reference list is one block of lines in the draft: one paragraph each
    last = doc.paragraphs[-1]
    lines = [ln for ln in src.split("## References")[1].strip().split("\n") if ln.strip()]
    last.text = lines[0]
    for ln in lines[1:]:
        para(ln)
doc.save(D + "Shortz_AllWISE_profile_fit_RNAAS.docx")
print("written", D + "Shortz_AllWISE_profile_fit_RNAAS.docx", len(doc.paragraphs), "paragraphs")
