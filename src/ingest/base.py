"""Base classes for document ingestion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class PageContent:
    """Content from a single page/slide."""
    page_number: int
    text: str
    tables: List[List[List[str]]] = field(default_factory=list)  # list of tables, each table is list of rows
    source_type: str = ""  # "pdf", "docx", "pptx"

    @property
    def has_content(self) -> bool:
        """Whether this page has any extractable content (text or tables)."""
        if self.text and self.text.strip():
            return True
        if self.tables:
            for table in self.tables:
                for row in table:
                    if any(cell.strip() for cell in row if cell):
                        return True
        return False

    @property
    def table_text(self) -> str:
        """Convert tables to readable text format."""
        if not self.tables:
            return ""
        parts = []
        for t_idx, table in enumerate(self.tables):
            rows_text = []
            for row in table:
                cells = [str(c).strip() for c in row if c and str(c).strip()]
                if cells:
                    rows_text.append(" | ".join(cells))
            if rows_text:
                parts.append("\n".join(rows_text))
        return "\n\n".join(parts)

    @property
    def combined_text(self) -> str:
        """Return text + table text combined."""
        parts = []
        if self.text and self.text.strip():
            parts.append(self.text.strip())
        tbl = self.table_text
        if tbl:
            parts.append(tbl)
        return "\n\n".join(parts)


@dataclass
class DocumentContent:
    """Full extracted document content."""
    file_path: str
    file_type: str
    pages: List[PageContent]
    total_pages: int
    metadata: dict = field(default_factory=dict)
    source_filename: str = ""

    @property
    def full_text(self) -> str:
        """Combine all page text AND table text into a single string.

        Tables are converted to pipe-separated text so their content
        is available to the LLM even if extract_text() returned nothing.
        """
        parts = []
        for p in self.pages:
            page_content = p.combined_text
            if page_content:
                parts.append(f"[Page {p.page_number}]\n{page_content}")
            else:
                # Still include page marker so LLM knows pages exist
                parts.append(f"[Page {p.page_number}]\n(このページのテキスト抽出なし)")
        return "\n\n".join(parts)

    @property
    def text_char_count(self) -> int:
        """Total characters of extracted text (excluding page markers)."""
        return sum(len(p.combined_text) for p in self.pages)

    @property
    def pages_with_content(self) -> int:
        """Number of pages that have extractable content."""
        return sum(1 for p in self.pages if p.has_content)

    @property
    def is_likely_image_pdf(self) -> bool:
        """Heuristic: if many pages exist but very little text, likely scanned/image PDF."""
        if self.total_pages == 0:
            return False
        content_ratio = self.pages_with_content / self.total_pages
        avg_chars = self.text_char_count / max(self.total_pages, 1)
        # If <30% of pages have content AND average chars per page is very low
        return content_ratio < 0.3 and avg_chars < 50

    def get_chunks(self, max_chars: int = 4000) -> List[str]:
        """Split document into chunks for LLM processing, preserving page markers."""
        chunks = []
        current_chunk = ""
        for page in self.pages:
            page_text = f"[Page {page.page_number}]\n{page.combined_text}\n\n"
            if len(current_chunk) + len(page_text) > max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = page_text
            else:
                current_chunk += page_text
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks

    def extraction_summary(self) -> str:
        """Return a human-readable summary of extraction results."""
        lines = [
            f"ファイル: {self.source_filename or self.file_path}",
            f"ページ数: {self.total_pages}",
            f"テキスト抽出ページ: {self.pages_with_content}/{self.total_pages}",
            f"合計文字数: {self.text_char_count:,}",
        ]
        if self.is_likely_image_pdf:
            lines.append("⚠ 画像ベースPDFの可能性（テキスト抽出率が低い）")
        return "\n".join(lines)
