"""
POST /api/upload - accepts image file, saves to /tmp, returns a URL.
Files are served via GET /api/upload/{filename}.
Background cleanup removes files older than 1 hour.
"""

import uuid
import os
import asyncio
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from backend.core.config import settings

router = APIRouter()

UPLOAD_DIR = Path("/tmp/batir_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_AGE_SECONDS = 3600  # 1 hour


@router.post("")
async def upload_image(file: UploadFile, background_tasks: BackgroundTasks) -> dict:
    """Accept an image and return a URL accessible by KIE.ai."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    ext = Path(file.filename or "").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    content = await file.read()
    filepath.write_bytes(content)

    # Schedule cleanup in background
    background_tasks.add_task(_cleanup_old_files)

    base_url = (settings.backend_base_url or "").rstrip("/")
    file_url = f"{base_url}/api/upload/{filename}"
    return {"url": file_url}



@router.get("/{filename}")
async def serve_upload(filename: str) -> FileResponse:
    """Serve the uploaded file so KIE.ai can download it."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))


async def _cleanup_old_files() -> None:
    """Remove files older than MAX_FILE_AGE_SECONDS."""
    now = time.time()
    for f in UPLOAD_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > MAX_FILE_AGE_SECONDS:
            try:
                f.unlink()
            except OSError:
                pass
