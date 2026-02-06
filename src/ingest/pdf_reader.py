"""PDF document text extraction with page numbers preserved.

Attempts to use pdfplumber for superior table extraction, falling back
to PyPDF2 when pdfplumber is not installed.
"""
import logging
from pathlib import Path
from typing import List, Optional

from .base import DocumentContent, PageContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Back-end availability flags
# ---------------------------------------------------------------------------
_HAS_PDFPLUMBER = False
_HAS_PYPDF2 = False

try:
    import pdfplumber  # type: ignore
    _HAS_PDFPLUMBER = True
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
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_pdf(file_path: str) -> DocumentContent:
    """Extract text (and tables when possible) from a PDF file.

    Tries pdfplumber first for richer extraction (tables, better layout
    handling, good Japanese-text support).  Falls back to PyPDF2 if
    pdfplumber is unavailable.

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

    if _HAS_PDFPLUMBER:
        logger.debug("Using pdfplumber for %s", file_path)
        return _extract_with_pdfplumber(file_path)

    if _HAS_PYPDF2:
        logger.debug("Using PyPDF2 (fallback) for %s", file_path)
        return _extract_with_pypdf2(file_path)

    raise RuntimeError(
        "No PDF extraction library available. "
        "Install pdfplumber (`pip install pdfplumber`) or "
        "PyPDF2 (`pip install PyPDF2`)."
    )
