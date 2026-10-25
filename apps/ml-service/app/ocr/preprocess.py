import io

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(Exception):
    """Raised for empty, oversized, corrupt, or unsupported image data."""


def load_and_validate(data: bytes, *, max_bytes: int = 15_000_000) -> Image.Image:
    if not data:
        raise InvalidImageError("empty file")
    if len(data) > max_bytes:
        raise InvalidImageError("file too large")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("unsupported or corrupt image") from exc
    # Respect EXIF orientation, then normalize to RGB. Conservative: no deskew/
    # contrast changes here — the original is preserved upstream for review.
    img = ImageOps.exif_transpose(img).convert("RGB")
    return img
