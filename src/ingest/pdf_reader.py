"""PDF document text extraction with page numbers preserved.

Extraction priority:
  1. pdfplumber  — best for Japanese text + tables
  2. PyMuPDF (fitz) — good fallback, handles more PDF types
  3. PyPDF2 — basic fallback

If primary extraction yields very little text, we automatically retry
with the next backend.  This handles cases where a PDF uses fonts or
encodings that one library can't decode but another can.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .base import DocumentContent, PageContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Back-end availability flags
# ---------------------------------------------------------------------------
_HAS_PDFPLUMBER = False
_HAS_PYMUPDF = False
_HAS_PYPDF2 = False

try:
    import pdfplumber  # type: ignore
    _HAS_PDFPLUMBER = True
except ImportError:
    pass

try:
    import fitz  # PyMuPDF  # type: ignore
    _HAS_PYMUPDF = True
except ImportError:
    pass

try:
    import PyPDF2  # type: ignore
    _HAS_PYPDF2 = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# pdfplumber extraction
# ---------------------------------------------------------------------------

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

                # --- text ------------------------------------------------
                try:
                    text = pdf_page.extract_text() or ""
                except Exception as exc:
                    logger.warning(
                        "pdfplumber: failed to extract text from page %d: %s",
                        page_number, exc,
                    )
                    text = ""

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

def _extract_with_pymupdf(file_path: str) -> DocumentContent:
    """Extract text from a PDF using PyMuPDF (fitz).

    PyMuPDF often succeeds where pdfplumber fails, especially with:
    - PDFs using CIDFont or Type3 fonts
    - PDFs with complex encoding mappings
    - PDFs generated from certain Asian-language tools
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

            try:
                # "text" mode extracts plain text preserving reading order
                text = page.get_text("text") or ""
            except Exception as exc:
                logger.warning(
                    "PyMuPDF: failed to extract text from page %d: %s",
                    page_number, exc,
                )
                text = ""

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
# Public API
# ---------------------------------------------------------------------------

_MIN_USEFUL_CHARS_PER_PAGE = 20  # below this, extraction probably failed


def extract_pdf(file_path: str) -> DocumentContent:
    """Extract text (and tables when possible) from a PDF file.

    Tries backends in priority order.  If the primary backend yields
    very little text, automatically retries with the next one.

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

    # Build ordered list of extraction backends
    backends = []
    if _HAS_PDFPLUMBER:
        backends.append(("pdfplumber", _extract_with_pdfplumber))
    if _HAS_PYMUPDF:
        backends.append(("PyMuPDF", _extract_with_pymupdf))
    if _HAS_PYPDF2:
        backends.append(("PyPDF2", _extract_with_pypdf2))

    if not backends:
        raise RuntimeError(
            "No PDF extraction library available. "
            "Install pdfplumber (`pip install pdfplumber`), "
            "PyMuPDF (`pip install pymupdf`), or "
            "PyPDF2 (`pip install PyPDF2`)."
        )

    best_result: Optional[DocumentContent] = None
    best_chars = 0

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

        except Exception as exc:
            logger.warning("PDF extraction with %s failed: %s", name, exc)
            continue

    # If no backend produced good results, return the best we have
    if best_result is not None:
        logger.warning(
            "All PDF backends produced low text yield. Best: %d chars. "
            "The PDF may be image-based (scanned).",
            best_chars,
        )
        return best_result

    raise RuntimeError(
        f"All PDF extraction backends failed for {file_path}. "
        "The file may be corrupted or password-protected."
    )
