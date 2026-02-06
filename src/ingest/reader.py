"""Main dispatcher for document ingestion.

Auto-detects file type by extension and delegates to the appropriate
reader module.

Supported formats
-----------------
* **.pdf**  — via :func:`~src.ingest.pdf_reader.extract_pdf`
* **.docx** — via :func:`~src.ingest.docx_reader.extract_docx`
* **.pptx** — via :func:`~src.ingest.pptx_reader.extract_pptx`

Usage::

    from src.ingest.reader import read_document

    doc = read_document("path/to/report.pdf")
    print(doc.full_text)
"""
import logging
from pathlib import Path

from .base import DocumentContent

logger = logging.getLogger(__name__)

# Map lowercase suffixes (including the dot) to reader callables.
_EXTENSION_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
}


def read_document(file_path: str) -> DocumentContent:
    """Read a document and return structured content with page numbers.

    The file type is determined by its extension.  The call is then
    forwarded to the matching reader:

    * ``.pdf``  -> :func:`pdf_reader.extract_pdf`
    * ``.docx`` -> :func:`docx_reader.extract_docx`
    * ``.pptx`` -> :func:`pptx_reader.extract_pptx`

    Parameters
    ----------
    file_path : str
        Path to the document file.

    Returns
    -------
    DocumentContent
        Extracted document content with per-page text and tables.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    ValueError
        If the file extension is not supported.
    RuntimeError
        If the appropriate library is missing or the file is corrupted.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    suffix = path.suffix.lower()
    file_type = _EXTENSION_MAP.get(suffix)

    if file_type is None:
        supported = ", ".join(sorted(_EXTENSION_MAP.keys()))
        raise ValueError(
            f"Unsupported file type '{suffix}' for: {file_path}. "
            f"Supported extensions: {supported}"
        )

    logger.info("Reading %s document: %s", file_type.upper(), file_path)

    if file_type == "pdf":
        from .pdf_reader import extract_pdf
        return extract_pdf(file_path)

    if file_type == "docx":
        from .docx_reader import extract_docx
        return extract_docx(file_path)

    if file_type == "pptx":
        from .pptx_reader import extract_pptx
        return extract_pptx(file_path)

    # Should be unreachable, but be defensive.
    raise ValueError(f"No reader implemented for file type: {file_type}")
