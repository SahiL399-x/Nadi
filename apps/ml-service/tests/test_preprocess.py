import io

import pytest
from PIL import Image

from app.ocr.preprocess import InvalidImageError, load_and_validate


def _png_bytes(size=(40, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_valid_png_loads_as_image():
    img = load_and_validate(_png_bytes())
    assert img.width == 40 and img.height == 20


def test_empty_bytes_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(b"")


def test_non_image_bytes_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(b"this is not an image")


def test_oversize_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(_png_bytes(), max_bytes=10)
