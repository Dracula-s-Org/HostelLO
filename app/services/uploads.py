"""Shared upload validation (HLD §6.2 hardening).

Uploads are bounded in size and verified by magic bytes — never by the
client-supplied content-type or filename — so a renamed script/HTML payload
cannot masquerade as an image/document.
"""
import os
from typing import Optional

from fastapi import HTTPException, UploadFile, status

from app.config import config

# Uploads live OUTSIDE the StaticFiles-served tree so they are never reachable by
# raw URL — every read is forced through the authenticated /api/assets/* routes.
UPLOAD_ROOT = os.path.realpath(os.path.join("var", "uploads"))
ROOM_DIR = os.path.join(UPLOAD_ROOT, "rooms")
KYC_DIR = os.path.join(UPLOAD_ROOT, "kyc")


def resolve_upload_path(ref: str) -> Optional[str]:
    """Resolve a stored local ref to an absolute path, but only if it stays inside
    UPLOAD_ROOT. Returns None for anything that escapes (path-traversal guard)."""
    if not ref:
        return None
    candidate = os.path.realpath(ref)
    try:
        if os.path.commonpath([UPLOAD_ROOT, candidate]) != UPLOAD_ROOT:
            return None
    except ValueError:  # different drives / relative-vs-absolute mismatch
        return None
    return candidate if os.path.isfile(candidate) else None

# extension chosen server-side from the sniffed type — client filename is never trusted
_IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff", ".jpg"),            # JPEG
    (b"\x89PNG\r\n\x1a\n", ".png"),       # PNG
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]


def _is_webp(data: bytes) -> bool:
    return len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP"


def _is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


async def read_capped(file: UploadFile) -> bytes:
    """Read at most MAX_UPLOAD_BYTES (+1 to detect overflow), bounding memory use."""
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MiB limit.",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload.")
    return data


def sniff_image_ext(data: bytes) -> str:
    """Return a safe extension if `data` is a real image, else 400."""
    for sig, ext in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return ext
    if _is_webp(data):
        return ".webp"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Upload a JPEG, PNG, WebP, or GIF image.",
    )


def sniff_document_ext(data: bytes) -> str:
    """KYC docs: real images or PDFs only."""
    if _is_pdf(data):
        return ".pdf"
    for sig, ext in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return ext
    if _is_webp(data):
        return ".webp"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported document. Upload a PDF or image of your ID.",
    )
