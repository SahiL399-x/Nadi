import io

import pypdfium2 as pdfium
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


def load_document(data: bytes, *, max_pages: int = 10, dpi: int = 200) -> list[Image.Image]:
    """PDF (magic %PDF) -> one RGB image per page (capped). Any other bytes ->
    [load_and_validate(data)]. Raises InvalidImageError on empty/corrupt input."""
    if not data:
        raise InvalidImageError("empty file")
    if data[:4] != b"%PDF":
        return [load_and_validate(data)]
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as exc:  # noqa: BLE001
        raise InvalidImageError("unsupported or corrupt pdf") from exc
    scale = dpi / 72.0
    images: list[Image.Image] = []
    for i in range(min(len(pdf), max_pages)):
        bitmap = pdf[i].render(scale=scale)
        images.append(bitmap.to_pil().convert("RGB"))
    return images
