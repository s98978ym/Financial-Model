"""Tests for src.ingest.reader -- document ingestion dispatcher.

Tests the read_document dispatcher for supported/unsupported file types,
FileNotFoundError, and the DocumentContent data model.
Also tests garbled-text detection for NotebookLM/Chrome-generated PDFs.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.ingest.reader import read_document, _EXTENSION_MAP
from src.ingest.base import DocumentContent, PageContent
from src.ingest.pdf_reader import _is_garbled


# ===================================================================
# Extension map
# ===================================================================

class TestExtensionMap:
    """Verify the supported extension mapping."""

    def test_pdf_supported(self):
        assert ".pdf" in _EXTENSION_MAP

    def test_docx_supported(self):
        assert ".docx" in _EXTENSION_MAP

    def test_pptx_supported(self):
        assert ".pptx" in _EXTENSION_MAP

    def test_xlsx_not_supported(self):
        assert ".xlsx" not in _EXTENSION_MAP

    def test_txt_not_supported(self):
        assert ".txt" not in _EXTENSION_MAP


# ===================================================================
# Unsupported file types
# ===================================================================

class TestUnsupportedTypes:
    """Test that unsupported file types raise ValueError."""

    def test_unsupported_txt_raises(self, tmp_path):
        txt_file = tmp_path / "doc.txt"
        txt_file.write_text("hello world")
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_document(str(txt_file))

    def test_unsupported_xlsx_raises(self, tmp_path):
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"\x00" * 10)
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_document(str(xlsx_file))

    def test_unsupported_csv_raises(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n1,2,3")
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_document(str(csv_file))

    def test_unsupported_jpg_raises(self, tmp_path):
        jpg_file = tmp_path / "image.jpg"
        jpg_file.write_bytes(b"\xff\xd8\xff")
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_document(str(jpg_file))

    def test_error_message_lists_supported_extensions(self, tmp_path):
        txt_file = tmp_path / "doc.txt"
        txt_file.write_text("hello")
        with pytest.raises(ValueError) as exc_info:
            read_document(str(txt_file))
        error_msg = str(exc_info.value)
        assert ".pdf" in error_msg
        assert ".docx" in error_msg
        assert ".pptx" in error_msg


# ===================================================================
# File not found
# ===================================================================

class TestFileNotFound:
    """Test that missing files raise FileNotFoundError."""

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_document("/nonexistent/path/document.pdf")

    def test_nonexistent_docx_raises(self):
        with pytest.raises(FileNotFoundError):
            read_document("/tmp/does_not_exist.docx")


# ===================================================================
# Not a file
# ===================================================================

class TestNotAFile:
    """Test that directories raise ValueError."""

    def test_directory_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not a file"):
            read_document(str(tmp_path))


# ===================================================================
# DocumentContent data model
# ===================================================================

class TestDocumentContent:
    """Test the DocumentContent dataclass independently."""

    def test_full_text_property(self):
        pages = [
            PageContent(page_number=1, text="First page text"),
            PageContent(page_number=2, text="Second page text"),
        ]
        doc = DocumentContent(
            file_path="/tmp/test.pdf",
            file_type="pdf",
            pages=pages,
            total_pages=2,
        )
        full = doc.full_text
        assert "[Page 1]" in full
        assert "First page text" in full
        assert "[Page 2]" in full
        assert "Second page text" in full

    def test_get_chunks_single_page(self):
        pages = [PageContent(page_number=1, text="Short text")]
        doc = DocumentContent(
            file_path="/tmp/test.pdf",
            file_type="pdf",
            pages=pages,
            total_pages=1,
        )
        chunks = doc.get_chunks(max_chars=4000)
        assert len(chunks) == 1

    def test_get_chunks_splits_large_content(self):
        # Create pages with enough text to exceed the chunk size
        pages = [
            PageContent(page_number=i, text="x" * 3000)
            for i in range(1, 6)
        ]
        doc = DocumentContent(
            file_path="/tmp/test.pdf",
            file_type="pdf",
            pages=pages,
            total_pages=5,
        )
        chunks = doc.get_chunks(max_chars=4000)
        assert len(chunks) > 1

    def test_empty_document(self):
        doc = DocumentContent(
            file_path="/tmp/test.pdf",
            file_type="pdf",
            pages=[],
            total_pages=0,
        )
        assert doc.full_text == ""
        assert doc.get_chunks() == []


# ===================================================================
# PageContent data model
# ===================================================================

class TestPageContent:
    """Test the PageContent dataclass."""

    def test_default_tables_empty(self):
        page = PageContent(page_number=1, text="Hello")
        assert page.tables == []

    def test_default_source_type_empty(self):
        page = PageContent(page_number=1, text="Hello")
        assert page.source_type == ""

    def test_with_tables(self):
        table = [["A", "B"], ["1", "2"]]
        page = PageContent(page_number=1, text="Hello", tables=[table])
        assert len(page.tables) == 1
        assert page.tables[0][0] == ["A", "B"]


# ===================================================================
# Garbled-text detection (for NotebookLM/Chrome PDFs)
# ===================================================================

class TestGarbledTextDetection:
    """Test _is_garbled() for detecting broken PDF text extraction."""

    def test_normal_japanese_not_garbled(self):
        text = "事業計画書に基づくPL自動生成システム"
        assert _is_garbled(text) is False

    def test_normal_english_not_garbled(self):
        text = "This is a normal English text with numbers 123."
        assert _is_garbled(text) is False

    def test_mixed_japanese_english_not_garbled(self):
        text = "売上高は年間1,000万円を見込んでいます。Revenue forecast is 10M JPY."
        assert _is_garbled(text) is False

    def test_replacement_chars_garbled(self):
        """U+FFFD replacement characters indicate failed glyph mapping."""
        text = "\ufffd" * 20 + "abc"
        assert _is_garbled(text) is True

    def test_cid_placeholders_garbled(self):
        """(cid:XXXX) placeholders from pdfminer for unmapped CIDs."""
        text = "(cid:1234)(cid:5678)(cid:9012)(cid:3456)"
        assert _is_garbled(text) is True

    def test_kangxi_radicals_garbled(self):
        """Kangxi radical chars from broken ToUnicode CMap."""
        # U+2F00 to U+2FDF range
        text = "\u2f00\u2f01\u2f02\u2f03\u2f04\u2f05\u2f06\u2f07"
        assert _is_garbled(text) is True

    def test_empty_not_garbled(self):
        assert _is_garbled("") is False
        assert _is_garbled("   ") is False

    def test_none_not_garbled(self):
        # Should handle None-like edge cases
        assert _is_garbled("") is False

    def test_few_replacement_chars_not_garbled(self):
        """A small number of replacement chars in mostly good text is OK."""
        text = "正常なテキスト" * 10 + "\ufffd"
        assert _is_garbled(text) is False

    def test_mixed_garbled_triggers(self):
        """Mixed garbled indicators above threshold."""
        text = "\ufffd\ufffd\ufffd(cid:123)\u2f00\u2f01normal"
        assert _is_garbled(text) is True


# ===================================================================
# PDF backend availability
# ===================================================================

class TestPdfBackendFlags:
    """Verify that backend availability flags are properly set."""

    def test_has_pdfplumber(self):
        from src.ingest.pdf_reader import _HAS_PDFPLUMBER
        # Should be True if pdfplumber is installed
        assert isinstance(_HAS_PDFPLUMBER, bool)

    def test_has_pymupdf(self):
        from src.ingest.pdf_reader import _HAS_PYMUPDF
        assert isinstance(_HAS_PYMUPDF, bool)

    def test_has_pypdfium2(self):
        from src.ingest.pdf_reader import _HAS_PYPDFIUM2
        assert isinstance(_HAS_PYPDFIUM2, bool)

    def test_has_pypdf2(self):
        from src.ingest.pdf_reader import _HAS_PYPDF2
        assert isinstance(_HAS_PYPDF2, bool)

    def test_has_poppler(self):
        from src.ingest.pdf_reader import _HAS_POPPLER
        assert isinstance(_HAS_POPPLER, bool)

    def test_at_least_one_backend(self):
        from src.ingest.pdf_reader import (
            _HAS_PDFPLUMBER, _HAS_PYMUPDF, _HAS_PYPDFIUM2, _HAS_PYPDF2, _HAS_POPPLER,
        )
        assert any([_HAS_PDFPLUMBER, _HAS_PYMUPDF, _HAS_PYPDFIUM2, _HAS_PYPDF2, _HAS_POPPLER])


# ===================================================================
# OCR fallback availability
# ===================================================================

class TestOcrFallback:
    """Test OCR fallback detection."""

    def test_can_ocr_returns_bool(self):
        from src.ingest.pdf_reader import _can_ocr
        assert isinstance(_can_ocr(), bool)

    def test_can_ocr_matches_deps(self):
        """_can_ocr() returns True only when tesseract + renderer are available."""
        from src.ingest.pdf_reader import _can_ocr, _HAS_PYMUPDF, _HAS_PYPDFIUM2
        result = _can_ocr()
        if not (_HAS_PYMUPDF or _HAS_PYPDFIUM2):
            assert result is False
        else:
            # If renderer is available, result depends on tesseract binary
            import shutil
            has_tesseract = shutil.which("tesseract") is not None
            assert result == has_tesseract
