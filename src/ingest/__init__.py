"""Document ingestion module — extract text from PDF, DOCX, and PPTX files.

Public API
----------
.. autofunction:: read_document
.. autoclass:: DocumentContent
.. autoclass:: PageContent
"""
from .base import DocumentContent, PageContent
from .reader import read_document

__all__ = [
    "read_document",
    "DocumentContent",
    "PageContent",
]
