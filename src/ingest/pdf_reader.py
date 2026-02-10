"""PDF document text extraction with page numbers preserved.

Extraction priority:
  1. pdfplumber  — best for Japanese text + tables
  2. PyMuPDF (fitz) — good fallback, handles more PDF types
  3. pypdfium2 — Chrome's own PDF engine (best for NotebookLM/Chrome PDFs)
  4. poppler pdftotext — C++ command-line tool, different implementation
  5. PyPDF2 — basic fallback

If primary extraction yields very little text, we automatically retry
with the next backend.  This handles cases where a PDF uses fonts or
encodings that one library can't decode but another can.

Special handling for NotebookLM / Chrome "Print to PDF":
  Chrome's Skia PDF backend uses glyph-ID encoding and often omits
  the /ToUnicode CMap, making text extraction impossible for most
  libraries.  pypdfium2 (PDFium bindings) uses the same engine as
  Chrome and can often extract text that others cannot.
  As a last resort, poppler's pdftotext (C++ implementation) is tried.
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .base import DocumentContent, PageContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Back-end availability flags
# ---------------------------------------------------------------------------
_HAS_PDFPLUMBER = False
_HAS_PYMUPDF = False
_HAS_PYPDFIUM2 = False
_HAS_PYPDF2 = False
_HAS_POPPLER = bool(shutil.which("pdftotext"))

try:
    import pdfplumber  # type: ignore
    _HAS_PDFPLUMBER = True
except BaseException:
    pass

try:
    import fitz  # PyMuPDF  # type: ignore
    _HAS_PYMUPDF = True
except BaseException:
    pass

try:
    import pypdfium2 as pdfium  # type: ignore
    _HAS_PYPDFIUM2 = True
except BaseException:
    pass

try:
    import PyPDF2  # type: ignore
    _HAS_PYPDF2 = True
except BaseException:
    pass


# ---------------------------------------------------------------------------
# Garbled-text detection
# ---------------------------------------------------------------------------
# Regex for (cid:XXXX) placeholders that pdfminer emits for unmapped glyphs
_CID_PATTERN = re.compile(r'\(cid:\d+\)')
# Kangxi Radicals range (U+2F00-U+2FDF) — often from broken ToUnicode maps
_KANGXI_PATTERN = re.compile(r'[\u2f00-\u2fdf]')


def _is_garbled(text: str) -> bool:
    """Detect if extracted text is garbled (unmappable glyphs).

    Returns True if the text contains a high proportion of:
    - U+FFFD replacement characters
    - (cid:XXXX) pdfminer placeholders
    - Kangxi Radical characters (wrong CMap mapping)
    """
    if not text or not text.strip():
        return False

    clean = text.strip()
    total = len(clean)
    if total == 0:
        return False

    # Count garbled indicators
    replacement_chars = clean.count('\ufffd')
    cid_matches = len(_CID_PATTERN.findall(clean))
    kangxi_chars = len(_KANGXI_PATTERN.findall(clean))

    garbled_count = replacement_chars + (cid_matches * 8) + kangxi_chars
    garbled_ratio = garbled_count / total

    if garbled_ratio > 0.15:
        logger.info(
            "Garbled text detected: %.1f%% (U+FFFD=%d, cid=%d, kangxi=%d / %d chars)",
            garbled_ratio * 100, replacement_chars, cid_matches, kangxi_chars, total,
        )
        return True
    return False


# ---------------------------------------------------------------------------
# pdfplumber extraction
# ---------------------------------------------------------------------------

def _extract_text_pdfplumber_page(pdf_page, page_number: int) -> str:
    """Try multiple pdfplumber text extraction methods for a single page.

    Falls back through:
    1. extract_text() — standard
    2. extract_text() with relaxed tolerances
    3. extract_words() — word-level (reconstructs text from individual words)
    """
    # Method 1: standard extract_text
    try:
        text = pdf_page.extract_text() or ""
        if text.strip() and not _is_garbled(text):
            return text
    except Exception as exc:
        logger.debug("pdfplumber: extract_text failed on page %d: %s", page_number, exc)

    # Method 2: relaxed tolerances (helps with some CJK layouts)
    try:
        text = pdf_page.extract_text(x_tolerance=5, y_tolerance=5) or ""
        if text.strip() and not _is_garbled(text):
            logger.info("pdfplumber: relaxed tolerance succeeded on page %d", page_number)
            return text
    except Exception as exc:
        logger.debug("pdfplumber: relaxed extract_text failed on page %d: %s", page_number, exc)

    # Method 3: word-level extraction and reconstruction
    try:
        words = pdf_page.extract_words(
            x_tolerance=3, y_tolerance=3,
            keep_blank_chars=True,
            use_text_flow=True,
        )
        if words:
            # Group words by approximate y-position (same line)
            lines: dict = {}
            for w in words:
                y_key = round(w["top"] / 5) * 5  # bucket by ~5pt
                if y_key not in lines:
                    lines[y_key] = []
                lines[y_key].append((w["x0"], w["text"]))
            # Sort lines by y, words by x within each line
            text_parts = []
            for y_key in sorted(lines.keys()):
                line_words = sorted(lines[y_key], key=lambda w: w[0])
                text_parts.append(" ".join(w[1] for w in line_words))
            text = "\n".join(text_parts)
            if text.strip() and not _is_garbled(text):
                logger.info("pdfplumber: word-level extraction succeeded on page %d (%d chars)", page_number, len(text))
                return text
    except Exception as exc:
        logger.debug("pdfplumber: extract_words failed on page %d: %s", page_number, exc)

    return ""


def _extract_with_pdfplumber(file_path: str) -> DocumentContent:
    """Extract text and tables from a PDF using pdfplumber."""
    import pdfplumber  # guaranteed available when called

    pages: List[PageContent] = []
    metadata: dict = {}

    try:
        with pdfplumber.open(file_path) as pdf:
            metadata = {
                k: v for k, v in (pdf.metadata or {}).items()
                if isinstance(v, (str, int, float, bool))
            }
            total_pages = len(pdf.pages)

            for idx, pdf_page in enumerate(pdf.pages):
                page_number = idx + 1

                # --- text (multi-method) ---------------------------------
                text = _extract_text_pdfplumber_page(pdf_page, page_number)

                # --- tables ----------------------------------------------
                tables: List[List[List[str]]] = []
                try:
                    raw_tables = pdf_page.extract_tables() or []
                    for raw_table in raw_tables:
                        cleaned_table: List[List[str]] = []
                        for row in raw_table:
                            cleaned_row = [
                                str(cell) if cell is not None else ""
                                for cell in row
                            ]
                            cleaned_table.append(cleaned_row)
                        tables.append(cleaned_table)
                except Exception as exc:
                    logger.warning(
                        "pdfplumber: failed to extract tables from page %d: %s",
                        page_number, exc,
                    )

                pages.append(
                    PageContent(
                        page_number=page_number,
                        text=text,
                        tables=tables,
                        source_type="pdf",
                    )
                )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to read PDF with pdfplumber: {file_path} — {exc}"
        ) from exc

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages if pages else 0,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


# ---------------------------------------------------------------------------
# PyMuPDF (fitz) extraction
# ---------------------------------------------------------------------------

def _extract_text_pymupdf_page(page) -> str:
    """Try multiple PyMuPDF text extraction methods for a single page.

    Falls back through progressively more aggressive methods:
    1. get_text("text") — standard plain text
    2. get_text("text", sort=True) — spatially sorted
    3. get_text("blocks") — text blocks
    4. get_text("words") — word-level, reconstruct lines
    5. get_text("html") — HTML extraction with tag stripping
    6. get_text("dict") — structured dict extraction
    7. get_text("rawdict") — raw character-level extraction
    8. Annotation / widget text extraction
    """
    page_num = page.number + 1

    # Method 1: standard text extraction
    try:
        text = page.get_text("text") or ""
        if text.strip() and not _is_garbled(text):
            return text
    except Exception:
        pass

    # Method 2: spatially sorted text (helps with multi-column layouts)
    try:
        text = page.get_text("text", sort=True) or ""
        if text.strip() and not _is_garbled(text):
            logger.info("PyMuPDF: sorted text succeeded on page %d", page_num)
            return text
    except Exception:
        pass

    # Method 3: blocks-based extraction
    try:
        blocks = page.get_text("blocks") or []
        block_texts = []
        for b in blocks:
            # blocks are tuples: (x0, y0, x1, y1, text, block_no, block_type)
            if len(b) >= 7 and b[6] == 0:  # type 0 = text block
                t = str(b[4]).strip()
                if t and not _is_garbled(t):
                    block_texts.append(t)
        if block_texts:
            text = "\n".join(block_texts)
            logger.info("PyMuPDF: blocks extraction succeeded on page %d (%d chars)", page_num, len(text))
            return text
    except Exception:
        pass

    # Method 4: word-level extraction with line reconstruction
    try:
        words = page.get_text("words") or []
        if words:
            # words are tuples: (x0, y0, x1, y1, word, block_no, line_no, word_no)
            # Group by line_no within each block
            lines_map: dict = {}
            for w in words:
                if len(w) >= 8:
                    word_text = str(w[4]).strip()
                    if word_text and not _is_garbled(word_text):
                        key = (w[5], w[6])  # (block_no, line_no)
                        if key not in lines_map:
                            lines_map[key] = []
                        lines_map[key].append((w[7], word_text))  # (word_no, text)

            if lines_map:
                text_lines = []
                for key in sorted(lines_map.keys()):
                    line_words = sorted(lines_map[key], key=lambda x: x[0])
                    text_lines.append(" ".join(w[1] for w in line_words))
                text = "\n".join(text_lines)
                if text.strip():
                    logger.info("PyMuPDF: words extraction succeeded on page %d (%d chars)", page_num, len(text))
                    return text
    except Exception as exc:
        logger.debug("PyMuPDF: words extraction failed on page %d: %s", page_num, exc)

    # Method 5: HTML extraction with tag stripping
    try:
        html = page.get_text("html") or ""
        if html.strip():
            # Strip HTML tags to get plain text
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&#\d+;', '', text)
            # Clean up whitespace
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            text = text.strip()
            if text and not _is_garbled(text) and len(text) > 10:
                logger.info("PyMuPDF: HTML extraction succeeded on page %d (%d chars)", page_num, len(text))
                return text
    except Exception as exc:
        logger.debug("PyMuPDF: HTML extraction failed on page %d: %s", page_num, exc)

    # Method 6: dict-based extraction (different from rawdict)
    try:
        d = page.get_text("dict")
        if d and "blocks" in d:
            text_parts = []
            for block in d["blocks"]:
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip() and not _is_garbled(line_text):
                            text_parts.append(line_text.strip())
            if text_parts:
                text = "\n".join(text_parts)
                logger.info("PyMuPDF: dict extraction succeeded on page %d (%d chars)", page_num, len(text))
                return text
    except Exception as exc:
        logger.debug("PyMuPDF: dict extraction failed on page %d: %s", page_num, exc)

    # Method 7: rawdict character-level extraction
    try:
        raw = page.get_text("rawdict")
        if raw and "blocks" in raw:
            chars = []
            for block in raw["blocks"]:
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip() and not _is_garbled(line_text):
                            chars.append(line_text.strip())
            if chars:
                text = "\n".join(chars)
                logger.info("PyMuPDF: rawdict extraction succeeded on page %d (%d chars)", page_num, len(text))
                return text
    except Exception:
        pass

    # Method 8: Extract text from annotations and widgets (form fields)
    try:
        annot_texts = []
        # Annotations (comments, notes, etc.)
        annot = page.first_annot
        while annot:
            info = annot.info
            if info:
                content = info.get("content", "")
                if content and content.strip():
                    annot_texts.append(content.strip())
            annot = annot.next
        # Widgets (form fields)
        widget = page.first_widget
        while widget:
            val = widget.field_value
            if val and str(val).strip():
                annot_texts.append(str(val).strip())
            widget = widget.next
        if annot_texts:
            text = "\n".join(annot_texts)
            if not _is_garbled(text):
                logger.info("PyMuPDF: annotation/widget extraction succeeded on page %d (%d chars)", page_num, len(text))
                return text
    except Exception as exc:
        logger.debug("PyMuPDF: annotation extraction failed on page %d: %s", page_num, exc)

    return ""


def _extract_with_pymupdf(file_path: str) -> DocumentContent:
    """Extract text from a PDF using PyMuPDF (fitz).

    PyMuPDF often succeeds where pdfplumber fails, especially with:
    - PDFs using CIDFont or Type3 fonts
    - PDFs with complex encoding mappings
    - PDFs generated from certain Asian-language tools

    Uses multiple extraction methods per page with garbled-text detection.
    """
    import fitz  # PyMuPDF

    pages: List[PageContent] = []
    metadata: dict = {}

    try:
        doc = fitz.open(file_path)

        # Metadata
        raw_meta = doc.metadata or {}
        for key in ("title", "author", "subject", "creator", "producer"):
            val = raw_meta.get(key)
            if val:
                metadata[key.capitalize()] = str(val)

        total_pages = doc.page_count

        for idx in range(total_pages):
            page_number = idx + 1
            page = doc[idx]

            text = _extract_text_pymupdf_page(page)

            # PyMuPDF can also extract tables (fitz 1.23+)
            tables: List[List[List[str]]] = []
            try:
                if hasattr(page, "find_tables"):
                    tab_finder = page.find_tables()
                    for tab in tab_finder.tables:
                        raw = tab.extract()
                        cleaned = [
                            [str(c) if c is not None else "" for c in row]
                            for row in raw
                        ]
                        tables.append(cleaned)
            except Exception as exc:
                logger.debug("PyMuPDF: table extraction failed on page %d: %s", page_number, exc)

            pages.append(
                PageContent(
                    page_number=page_number,
                    text=text,
                    tables=tables,
                    source_type="pdf",
                )
            )

        doc.close()

    except Exception as exc:
        raise RuntimeError(
            f"Failed to read PDF with PyMuPDF: {file_path} — {exc}"
        ) from exc

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages if pages else 0,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


# ---------------------------------------------------------------------------
# pypdfium2 extraction (Chrome's PDFium engine — best for NotebookLM PDFs)
# ---------------------------------------------------------------------------

def _extract_with_pypdfium2(file_path: str) -> DocumentContent:
    """Extract text from a PDF using pypdfium2 (PDFium bindings).

    PDFium is the PDF engine used by Google Chrome.  It uses the same
    rendering pipeline that displays NotebookLM PDFs correctly, so it
    can often extract text from Chrome-generated PDFs where other
    libraries fail due to missing /ToUnicode CMap entries.
    """
    import pypdfium2 as pdfium  # guaranteed available when called

    pages: List[PageContent] = []
    metadata: dict = {}

    try:
        doc = pdfium.PdfDocument(file_path)
        total_pages = len(doc)

        for idx in range(total_pages):
            page_number = idx + 1
            page = doc[idx]

            text = ""
            try:
                textpage = page.get_textpage()
                text = textpage.get_text_bounded() or ""
                textpage.close()

                # If bounded text fails, try range-based extraction
                if not text.strip() or _is_garbled(text):
                    textpage = page.get_textpage()
                    n_chars = textpage.count_chars()
                    if n_chars > 0:
                        text = textpage.get_text_range(0, n_chars) or ""
                    textpage.close()
            except Exception as exc:
                logger.debug(
                    "pypdfium2: text extraction failed on page %d: %s",
                    page_number, exc,
                )
                text = ""

            if _is_garbled(text):
                text = ""

            pages.append(
                PageContent(
                    page_number=page_number,
                    text=text,
                    tables=[],  # pypdfium2 doesn't do table extraction
                    source_type="pdf",
                )
            )

            page.close()
        doc.close()

    except Exception as exc:
        raise RuntimeError(
            f"Failed to read PDF with pypdfium2: {file_path} — {exc}"
        ) from exc

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages if pages else 0,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


# ---------------------------------------------------------------------------
# poppler pdftotext extraction (command-line tool)
# ---------------------------------------------------------------------------

def _extract_with_poppler(file_path: str) -> DocumentContent:
    """Extract text from a PDF using poppler's pdftotext command-line tool.

    poppler is a completely different C++ PDF implementation and sometimes
    succeeds where Python libraries fail.  It handles some CIDFont and
    ToUnicode edge cases differently.
    """
    pages: List[PageContent] = []
    metadata: dict = {}

    try:
        # First get total pages via pdfinfo
        total_pages = 0
        try:
            info_out = subprocess.run(
                ["pdfinfo", file_path],
                capture_output=True, text=True, timeout=30,
            )
            for line in info_out.stdout.splitlines():
                if line.startswith("Pages:"):
                    total_pages = int(line.split(":", 1)[1].strip())
                elif line.startswith("Title:"):
                    metadata["Title"] = line.split(":", 1)[1].strip()
                elif line.startswith("Author:"):
                    metadata["Author"] = line.split(":", 1)[1].strip()
        except Exception:
            pass

        # Extract text page by page for proper page splitting
        if total_pages > 0:
            for page_num in range(1, total_pages + 1):
                try:
                    result = subprocess.run(
                        ["pdftotext", "-f", str(page_num), "-l", str(page_num),
                         "-layout", file_path, "-"],
                        capture_output=True, text=True, timeout=30,
                    )
                    text = result.stdout or ""
                    if _is_garbled(text):
                        text = ""
                except Exception as exc:
                    logger.debug("poppler: page %d extraction failed: %s", page_num, exc)
                    text = ""

                pages.append(
                    PageContent(
                        page_number=page_num,
                        text=text.strip(),
                        tables=[],
                        source_type="pdf",
                    )
                )
        else:
            # Fallback: extract all pages at once
            result = subprocess.run(
                ["pdftotext", "-layout", file_path, "-"],
                capture_output=True, text=True, timeout=60,
            )
            text = (result.stdout or "").strip()
            if text and not _is_garbled(text):
                pages.append(
                    PageContent(
                        page_number=1,
                        text=text,
                        tables=[],
                        source_type="pdf",
                    )
                )
                total_pages = 1

    except Exception as exc:
        raise RuntimeError(
            f"Failed to read PDF with poppler pdftotext: {file_path} — {exc}"
        ) from exc

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages if pages else 0,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


# ---------------------------------------------------------------------------
# PyPDF2 extraction (fallback)
# ---------------------------------------------------------------------------

def _extract_with_pypdf2(file_path: str) -> DocumentContent:
    """Extract text from a PDF using PyPDF2 (no table extraction)."""
    import PyPDF2  # guaranteed available when called

    pages: List[PageContent] = []
    metadata: dict = {}

    try:
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)

            # Metadata
            raw_meta = reader.metadata
            if raw_meta:
                for key in ("/Title", "/Author", "/Subject", "/Creator", "/Producer"):
                    val = raw_meta.get(key)
                    if val:
                        metadata[key.lstrip("/")] = str(val)

            total_pages = len(reader.pages)

            for idx, pdf_page in enumerate(reader.pages):
                page_number = idx + 1
                try:
                    text = pdf_page.extract_text() or ""
                except Exception as exc:
                    logger.warning(
                        "PyPDF2: failed to extract text from page %d: %s",
                        page_number, exc,
                    )
                    text = ""

                pages.append(
                    PageContent(
                        page_number=page_number,
                        text=text,
                        tables=[],
                        source_type="pdf",
                    )
                )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to read PDF with PyPDF2: {file_path} — {exc}"
        ) from exc

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages if pages else 0,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


# ---------------------------------------------------------------------------
# OCR fallback (last resort for NotebookLM / Type3 font PDFs)
# ---------------------------------------------------------------------------

def _render_pages_fitz(file_path: str) -> list:
    """Render PDF pages to PIL Images using PyMuPDF (fitz) at 300 DPI."""
    import io

    import fitz  # PyMuPDF
    from PIL import Image

    doc = fitz.open(file_path)
    images = []
    for idx in range(doc.page_count):
        page = doc[idx]
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        images.append(Image.open(io.BytesIO(img_bytes)))
    doc.close()
    return images


def _render_pages_pypdfium2(file_path: str) -> list:
    """Render PDF pages to PIL Images using pypdfium2 at 300 DPI."""
    import pypdfium2 as pdfium  # type: ignore

    doc = pdfium.PdfDocument(file_path)
    images = []
    for idx in range(len(doc)):
        page = doc[idx]
        # scale = DPI / 72
        bitmap = page.render(scale=300 / 72)
        pil_image = bitmap.to_pil()
        images.append(pil_image)
        page.close()
    doc.close()
    return images


def _extract_with_ocr(file_path: str) -> DocumentContent:
    """Extract text from a PDF by rendering pages as images and running OCR.

    This is the last-resort fallback for PDFs where ALL text extraction
    backends fail (e.g. NotebookLM / Chrome PDFs with Type3 fonts and
    missing /ToUnicode CMap).

    Page rendering tries PyMuPDF first, then pypdfium2 as fallback.
    Requires: pytesseract, Pillow, tesseract-ocr, and at least one of
    PyMuPDF or pypdfium2 for page rendering.
    """
    import pytesseract
    from PIL import Image  # noqa: F401

    pages: List[PageContent] = []
    metadata: dict = {}

    # --- Render pages to images (try fitz first, then pypdfium2) ---
    images: list = []
    render_errors: List[str] = []

    if _HAS_PYMUPDF:
        try:
            images = _render_pages_fitz(file_path)
            logger.info("OCR: rendered %d pages via PyMuPDF", len(images))
        except BaseException as exc:
            render_errors.append(f"PyMuPDF render: {exc}")
            logger.debug("OCR: PyMuPDF rendering failed: %s", exc)

    if not images and _HAS_PYPDFIUM2:
        try:
            images = _render_pages_pypdfium2(file_path)
            logger.info("OCR: rendered %d pages via pypdfium2", len(images))
        except BaseException as exc:
            render_errors.append(f"pypdfium2 render: {exc}")
            logger.debug("OCR: pypdfium2 rendering failed: %s", exc)

    if not images:
        raise RuntimeError(
            f"OCR fallback: cannot render pages for {file_path}. "
            f"Need PyMuPDF or pypdfium2 for rendering. "
            f"Errors: {'; '.join(render_errors)}"
        )

    total_pages = len(images)
    logger.info(
        "OCR fallback: processing %d pages at 300 DPI for %s",
        total_pages, Path(file_path).name,
    )

    for idx, img in enumerate(images):
        page_number = idx + 1
        try:
            # Run Tesseract OCR (Japanese + English)
            text = pytesseract.image_to_string(img, lang="jpn+eng")
            text = (text or "").strip()

            if text:
                logger.info(
                    "OCR: page %d → %d chars extracted",
                    page_number, len(text),
                )
        except Exception as exc:
            logger.warning("OCR failed on page %d: %s", page_number, exc)
            text = ""

        pages.append(
            PageContent(
                page_number=page_number,
                text=text,
                tables=[],
                source_type="pdf",
            )
        )

    return DocumentContent(
        file_path=str(file_path),
        file_type="pdf",
        pages=pages,
        total_pages=total_pages,
        metadata=metadata,
        source_filename=Path(file_path).name,
    )


def _can_ocr() -> bool:
    """Check if OCR dependencies are available.

    Requires:
    - pytesseract + tesseract binary (for OCR)
    - Pillow (for image handling)
    - At least one of PyMuPDF or pypdfium2 (for page rendering)
    """
    try:
        import pytesseract  # noqa: F811
        from PIL import Image  # noqa: F401
        # Verify tesseract binary exists
        pytesseract.get_tesseract_version()
    except BaseException:
        return False

    # Need at least one renderer
    if not (_HAS_PYMUPDF or _HAS_PYPDFIUM2):
        return False

    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_MIN_USEFUL_CHARS_PER_PAGE = 20  # below this, extraction probably failed
_MAX_FILE_SIZE_FOR_OCR_MB = 2  # Skip OCR for files above this size
_MAX_BACKENDS_TO_TRY = 3  # Limit backend attempts for large files


def extract_pdf(file_path: str) -> DocumentContent:
    """Extract text (and tables when possible) from a PDF file.

    Tries backends in priority order.  If the primary backend yields
    very little text, automatically retries with the next one.
    If ALL backends fail, falls back to OCR (renders pages as images
    and runs Tesseract OCR for Japanese + English).

    Parameters
    ----------
    file_path : str
        Path to the PDF file.

    Returns
    -------
    DocumentContent
        Extracted document with per-page text and tables.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    RuntimeError
        If no PDF library is installed or the file cannot be read.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Log file size for memory management
    file_size_mb = path.stat().st_size / (1024 * 1024)
    logger.info("PDF file size: %.1f MB \u2014 %s", file_size_mb, path.name)

    # Build ordered list of extraction backends
    backends = []
    if _HAS_PDFPLUMBER:
        backends.append(("pdfplumber", _extract_with_pdfplumber))
    if _HAS_PYMUPDF:
        backends.append(("PyMuPDF", _extract_with_pymupdf))
    if _HAS_PYPDFIUM2:
        backends.append(("pypdfium2", _extract_with_pypdfium2))
    if _HAS_POPPLER:
        backends.append(("poppler", _extract_with_poppler))
    if _HAS_PYPDF2:
        backends.append(("PyPDF2", _extract_with_pypdf2))

    # Limit backends for large files to save memory
    if file_size_mb > _MAX_FILE_SIZE_FOR_OCR_MB and len(backends) > _MAX_BACKENDS_TO_TRY:
        logger.info("Large file (%.1f MB) \u2014 limiting to %d backends", file_size_mb, _MAX_BACKENDS_TO_TRY)
        backends = backends[:_MAX_BACKENDS_TO_TRY]

    if not backends:
        raise RuntimeError(
            "No PDF extraction library available. "
            "Install pdfplumber (`pip install pdfplumber`), "
            "PyMuPDF (`pip install pymupdf`), "
            "pypdfium2 (`pip install pypdfium2`), or "
            "PyPDF2 (`pip install PyPDF2`)."
        )

    best_result: Optional[DocumentContent] = None
    best_chars = 0
    backend_errors: List[str] = []

    for name, extract_fn in backends:
        try:
            logger.info("Trying PDF extraction with %s for %s", name, path.name)
            result = extract_fn(file_path)
            char_count = result.text_char_count
            logger.info(
                "%s: extracted %d chars from %d/%d pages",
                name, char_count, result.pages_with_content, result.total_pages,
            )

            # If we got good content, use it immediately
            avg_chars = char_count / max(result.total_pages, 1)
            if avg_chars >= _MIN_USEFUL_CHARS_PER_PAGE:
                logger.info("Using %s result (%.0f avg chars/page)", name, avg_chars)
                return result

            # Otherwise, keep track of the best result so far
            if char_count > best_chars:
                best_chars = char_count
                best_result = result
            if char_count == 0:
                backend_errors.append(f"{name}: 0 chars extracted")

        except BaseException as exc:
            logger.warning("PDF extraction with %s failed: %s", name, exc)
            backend_errors.append(f"{name}: {exc}")
            continue

    # --- OCR fallback: all text backends failed or produced very little ---
    if best_chars < _MIN_USEFUL_CHARS_PER_PAGE:
        # Skip OCR for large files to prevent OOM on limited-memory servers
        if file_size_mb > _MAX_FILE_SIZE_FOR_OCR_MB:
            logger.warning("Skipping OCR for large file (%.1f MB) to prevent OOM", file_size_mb)
            if best_result is not None:
                return best_result
            return DocumentContent(
                file_path=str(file_path), file_type="pdf",
                pages=[PageContent(page_number=1, text="", tables=[], source_type="pdf")],
                total_pages=1, metadata={}, source_filename=path.name,
            )
        ocr_available = _can_ocr()
        logger.info(
            "All text extraction backends produced ≤%d chars (best: %d). "
            "OCR available: %s. Attempting OCR for %s",
            _MIN_USEFUL_CHARS_PER_PAGE, best_chars, ocr_available, path.name,
        )
        if ocr_available:
            try:
                ocr_result = _extract_with_ocr(file_path)
                ocr_chars = ocr_result.text_char_count
                logger.info("OCR extracted %d chars from %d pages",
                            ocr_chars, ocr_result.total_pages)
                if ocr_chars > best_chars:
                    return ocr_result
            except BaseException as exc:
                logger.warning("OCR fallback failed: %s", exc)
                backend_errors.append(f"OCR: {exc}")
        else:
            # Log why OCR is unavailable to help with debugging
            _ocr_missing: List[str] = []
            try:
                import pytesseract  # noqa: F811
                pytesseract.get_tesseract_version()
            except BaseException:
                _ocr_missing.append("tesseract-ocr")
            try:
                from PIL import Image  # noqa: F401
            except BaseException:
                _ocr_missing.append("Pillow")
            if not (_HAS_PYMUPDF or _HAS_PYPDFIUM2):
                _ocr_missing.append("PyMuPDF or pypdfium2 (for rendering)")
            logger.warning("OCR unavailable — missing: %s", ", ".join(_ocr_missing) or "unknown")
            backend_errors.append(f"OCR unavailable (missing: {', '.join(_ocr_missing)})")

    # Return the best text-extraction result we have (even if low quality)
    if best_result is not None:
        logger.warning(
            "All PDF backends produced low text yield. Best: %d chars. "
            "The PDF may use fonts that prevent text extraction.",
            best_chars,
        )
        return best_result

    # Build detailed error message for debugging
    error_detail = "; ".join(backend_errors) if backend_errors else "no backends available"
    raise RuntimeError(
        f"All PDF extraction backends failed for {file_path}. "
        f"Details: {error_detail}"
    )
