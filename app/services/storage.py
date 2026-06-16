"""Room-image storage: Cloudinary when configured, gated local store otherwise.

Local files are written OUTSIDE the StaticFiles tree (var/uploads/rooms) and are
only ever served through the authenticated /api/assets/rooms route. Uploads are
size-bounded and verified by magic bytes (app/services/uploads.py).
"""
import os
import uuid

from fastapi import UploadFile

from app.config import config
from app.services.uploads import ROOM_DIR, read_capped, sniff_image_ext


def cloudinary_enabled() -> bool:
    return bool(config.CLOUDINARY_URL)


async def save_room_image(file: UploadFile) -> str:
    """Returns a renderable reference: an https Cloudinary URL, or a gated local
    path (var/uploads/rooms/...) served via /api/assets."""
    data = await read_capped(file)
    ext = sniff_image_ext(data)  # raises 400 if not a real image

    if cloudinary_enabled():
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
        result = cloudinary.uploader.upload(
            data, folder="hostello/rooms", resource_type="image"
        )
        return result["secure_url"]

    os.makedirs(ROOM_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(ROOM_DIR, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path
