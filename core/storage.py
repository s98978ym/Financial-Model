"""Supabase Storage helper for file upload/download.

Supports two modes:
- Supabase Storage when SUPABASE_URL + SUPABASE_SERVICE_KEY are set
- Local filesystem fallback for development
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "documents")
LOCAL_UPLOAD_DIR = os.environ.get("LOCAL_UPLOAD_DIR", "/tmp/plgen_uploads")

_supabase_client = None


def _get_supabase():
    """Lazy-init Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized")
        return _supabase_client
    except ImportError:
        logger.warning("supabase package not installed — using local storage")
        return None
    except Exception as e:
        logger.warning("Failed to init Supabase: %s — using local storage", e)
        return None


def _use_supabase() -> bool:
    return _get_supabase() is not None


def upload_file(
    project_id: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload file and return storage path.

    Returns a path like 'projects/{project_id}/{filename}' that can be
    used later to download the file.
    """
    storage_path = f"projects/{project_id}/{filename}"

    if _use_supabase():
        client = _get_supabase()
        client.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type},
        )
        logger.info("Uploaded to Supabase: %s", storage_path)
    else:
        local_dir = Path(LOCAL_UPLOAD_DIR) / "projects" / project_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename
        local_path.write_bytes(content)
        logger.info("Saved locally: %s", local_path)

    return storage_path


def download_file(storage_path: str) -> Optional[bytes]:
    """Download file content by storage path."""
    if _use_supabase():
        client = _get_supabase()
        response = client.storage.from_(STORAGE_BUCKET).download(storage_path)
        return response
    else:
        local_path = Path(LOCAL_UPLOAD_DIR) / storage_path
        if local_path.exists():
            return local_path.read_bytes()
        return None


def get_public_url(storage_path: str) -> str:
    """Get a public (or signed) URL for the file."""
    if _use_supabase():
        client = _get_supabase()
        result = client.storage.from_(STORAGE_BUCKET).create_signed_url(
            storage_path, expires_in=3600,
        )
        return result.get("signedURL", "")
    else:
        return f"file://{Path(LOCAL_UPLOAD_DIR) / storage_path}"


def delete_file(storage_path: str) -> bool:
    """Delete a file from storage."""
    if _use_supabase():
        client = _get_supabase()
        client.storage.from_(STORAGE_BUCKET).remove([storage_path])
        return True
    else:
        local_path = Path(LOCAL_UPLOAD_DIR) / storage_path
        if local_path.exists():
            local_path.unlink()
            return True
        return False
