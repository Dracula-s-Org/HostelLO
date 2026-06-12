"""Room-image storage: Cloudinary when configured, local /static/uploads
fallback for dev. Render free tier has no persistent disk, so production
must set CLOUDINARY_URL (Dev B infra deliverable).
"""
import os
import uuid

from fastapi import UploadFile

from app.config import config

ROOM_UPLOAD_DIR = os.path.join("static", "uploads", "rooms")


def cloudinary_enabled() -> bool:
    return bool(config.CLOUDINARY_URL)


async def save_room_image(file: UploadFile) -> str:
    """Returns a renderable reference: an https Cloudinary URL, or a local
    /static path in dev."""
    data = await file.read()
    if cloudinary_enabled():
        os.environ.setdefault("CLOUDINARY_URL", config.CLOUDINARY_URL)
        import cloudinary.uploader

        result = cloudinary.uploader.upload(
            data, folder="hostello/rooms", resource_type="image"
        )
        return result["secure_url"]

    os.makedirs(ROOM_UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(ROOM_UPLOAD_DIR, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return f"/static/uploads/rooms/{name}"
