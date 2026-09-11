"""
Export engine — section 3 of the original app.py.

Builds genuinely valid .docx, .pdf and .zip payloads from OOXML / PDF
primitives using only the standard library, so the project needs neither
python-docx nor reportlab.

Pure functions: bytes in, bytes out. No Streamlit import, no session state —
which makes this the one module you can unit-test without a running app.
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile

from core.config import CURRENT_USER


def _xesc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_docx(title: str, subtitle: str, blocks: list, table: dict | None = None) -> bytes:
    """Create a genuinely valid, Word-openable .docx from OOXML primitives.

    blocks : list of (style, text) where style ∈ {h1, h2, body, bullet, meta}
    table  : {"caption": str, "headers": [...], "rows": [[...], ...]}
    """
    def para(text: str, size: int = 22, bold: bool = False,
             color: str = "1E293B", space_after: int = 120, align: str = "left") -> str:
        return (
            "<w:p><w:pPr>"
            f'<w:spacing w:after="{space_after}"/>'
            f'<w:jc w:val="{align}"/>'
            "</w:pPr>"
            "<w:r><w:rPr>"
            f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
            f'{"<w:b/>" if bold else ""}'
            f'<w:color w:val="{color}"/><w:sz w:val="{size}"/>'
            "</w:rPr>"
            f'<w:t xml:space="preserve">{_xesc(text)}</w:t>'
            "</w:r></w:p>"
        )

    def cell(text: str, width: int, header: bool = False) -> str:
        shade = '<w:shd w:val="clear" w:fill="0F172A"/>' if header else ""
        color = "FFFFFF" if header else "1E293B"
        return (
            "<w:tc><w:tcPr>"
            f'<w:tcW w:w="{width}" w:type="dxa"/>{shade}'
            "</w:tcPr>"
            "<w:p><w:pPr><w:spacing w:after='0'/></w:pPr><w:r><w:rPr>"
            f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
            f'{"<w:b/>" if header else ""}<w:color w:val="{color}"/><w:sz w:val="19"/>'
            f'</w:rPr><w:t xml:space="preserve">{_xesc(text)}</w:t></w:r></w:p>'
            "</w:tc>"
        )

    body: list[str] = [
        para(title, size=32, bold=True, color="0F172A", space_after=40),
        para(subtitle, size=19, color="64748B", space_after=260),
    ]

    for style, text in blocks:
        if style == "h1":
            body.append(para(text, size=26, bold=True, color="0F172A", space_after=100))
        elif style == "h2":
            body.append(para(text, size=23, bold=True, color="0F172A", space_after=90))
        elif style == "bullet":
            body.append(para("•  " + text, size=21))
        elif style == "meta":
            body.append(para(text, size=17, color="64748B"))
        else:
            body.append(para(text, size=21))

    if table:
        body.append(para(table.get("caption", ""), size=21, bold=True, space_after=90))
        widths = [2600] * len(table["headers"])
        rows_xml = ["<w:tr>" + "".join(cell(h, w, True)
                                       for h, w in zip(table["headers"], widths)) + "</w:tr>"]
        for row in table["rows"]:
            rows_xml.append("<w:tr>" + "".join(cell(c, w)
                                               for c, w in zip(row, widths)) + "</w:tr>")
        borders = (
            "<w:tblBorders>"
            + "".join(
                f'<w:{edge} w:val="single" w:sz="6" w:color="CBD5E1"/>'
                for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
            )
            + "</w:tblBorders>"
        )
        body.append(
            "<w:tbl><w:tblPr><w:tblW w:w='0' w:type='auto'/>"
            + borders
            + "</w:tblPr>"
            + "".join(rows_xml)
            + "</w:tbl>"
            + para("", size=18, space_after=140)
        )

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(body) +
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418"/></w:sectPr>'
        "</w:body></w:document>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
    return buf.getvalue()


def build_pdf(title: str, lines: list[str]) -> bytes:
    """Create a valid, audit-ready multi-page PDF using only the standard library."""
    translit = {
        "—": "-", "–": "-", "―": "-", "•": "-", "·": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...",
        "✔": "[OK]", "✘": "[X]", "❌": "[X]", "⏳": "[PENDING]", "→": "->",
        "≤": "<=", "≥": ">=", "×": "x", "™": "(TM)",
    }

    def esc(s: str) -> str:
        for src, dst in translit.items():
            s = s.replace(src, dst)
        s = s.encode("latin-1", "replace").decode("latin-1")
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    per_page = 44
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[""]]

    objects: dict[int, bytes] = {}
    n = len(pages)
    page_ids = [4 + 2 * i for i in range(n)]
    content_ids = [5 + 2 * i for i in range(n)]

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Count {n} /Kids [{kids}] >>".encode()
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    bold_font_id = 3 + 2 * n + 1
    objects[bold_font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

    for idx, page_lines in enumerate(pages):
        pid, cid = page_ids[idx], content_ids[idx]
        objects[pid] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 {bold_font_id} 0 R >> >> "
            f"/Contents {cid} 0 R >>"
        ).encode()

        stream = ["BT /F2 15 Tf 1 0 0 1 56 786 Tm 0.06 0.09 0.16 rg",
                  f"({esc(title)}) Tj ET",
                  "0.02 0.71 0.83 RG 1.2 w 56 779 m 539 779 l S"]
        y = 756.0
        for ln in page_lines:
            if ln.startswith("## "):
                stream.append(
                    f"BT /F2 11 Tf 1 0 0 1 56 {y:.1f} Tm 0.06 0.09 0.16 rg "
                    f"({esc(ln[3:])}) Tj ET"
                )
            elif ln.startswith("|"):
                stream.append(
                    f"BT /F1 8.6 Tf 1 0 0 1 60 {y:.1f} Tm 0.11 0.16 0.24 rg "
                    f"({esc(ln)}) Tj ET"
                )
            else:
                stream.append(
                    f"BT /F1 9.5 Tf 1 0 0 1 56 {y:.1f} Tm 0.11 0.16 0.24 rg "
                    f"({esc(ln)}) Tj ET"
                )
            y -= 16.0
        stream.append(
            f"BT /F1 7.5 Tf 1 0 0 1 56 44 Tm 0.58 0.64 0.72 rg "
            f"({esc(f'VaultComply AI — Audit-Ready Export — Page {idx + 1} of {n}')}) Tj ET"
        )
        content = "\n".join(stream).encode("latin-1", "replace")
        objects[cid] = b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"

    xref_pos = len(out)
    max_obj = max(objects)
    out += f"xref\n0 {max_obj + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_obj + 1):
        out += (f"{offsets.get(num, 0):010d} 00000 n \n").encode()
    out += (
        f"trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def build_bundle(category: str, docx_bytes: bytes, pdf_bytes: bytes,
                 manifest_lines: list[str], vault_files: list[str]) -> bytes:
    """ePerolehan-style submission bundle (.zip) with manifest and checksums."""
    import hashlib

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"01_Submission/{category}_Draft_{stamp}.docx", docx_bytes)
        z.writestr(f"01_Submission/{category}_AuditReady_{stamp}.pdf", pdf_bytes)
        z.writestr("02_Manifest/SUBMISSION_MANIFEST.txt", "\n".join(manifest_lines))
        z.writestr(
            "02_Manifest/VAULT_INDEX.txt",
            "INDEXED SOURCE DOCUMENTS (Single-Tenant Namespace)\n"
            + "\n".join(f"  [INDEXED] {f}" for f in vault_files),
        )
        z.writestr(
            "03_Integrity/CHECKSUMS.sha256",
            f"{hashlib.sha256(docx_bytes).hexdigest()}  {category}_Draft_{stamp}.docx\n"
            f"{hashlib.sha256(pdf_bytes).hexdigest()}  {category}_AuditReady_{stamp}.pdf\n",
        )
        z.writestr(
            "03_Integrity/SIGNOFF_ATTESTATION.txt",
            "HUMAN-IN-THE-LOOP SIGN-OFF ATTESTATION\n"
            "=======================================\n"
            f"Document class      : {category}\n"
            f"Approved by         : {CURRENT_USER}\n"
            f"Approval timestamp  : {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n"
            "Prototype mode      : Local processing; no external AI API configured by default\n"
            "Grounding           : Citations originate from locally parsed vault chunks\n"
            "Governance          : Human approval recorded separately from compliance scoring\n"
            "Note                : This prototype does not represent an external security certification\n",
        )
    return buf.getvalue()
