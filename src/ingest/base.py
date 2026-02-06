"""Base classes for document ingestion."""
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

@dataclass
class DocumentContent:
    """Full extracted document content."""
    file_path: str
    file_type: str
    pages: List[PageContent]
    total_pages: int
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(
            f"[Page {p.page_number}]\n{p.text}" for p in self.pages
        )

    def get_chunks(self, max_chars: int = 4000) -> List[str]:
        """Split document into chunks for LLM processing, preserving page markers."""
        chunks = []
        current_chunk = ""
        for page in self.pages:
            page_text = f"[Page {page.page_number}]\n{page.text}\n\n"
            if len(current_chunk) + len(page_text) > max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = page_text
            else:
                current_chunk += page_text
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks
