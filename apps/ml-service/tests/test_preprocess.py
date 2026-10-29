import io

import pytest
from PIL import Image

from app.ocr.preprocess import InvalidImageError, enhance, load_and_validate, load_document


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


def _pdf_bytes(pages: int = 1) -> bytes:
    imgs = [Image.new("RGB", (240, 320), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def test_load_document_image_returns_single_image():
    out = load_document(_png_bytes())
    assert len(out) == 1 and out[0].mode == "RGB"


def test_load_document_pdf_rasterizes_each_page():
    out = load_document(_pdf_bytes(pages=3))
    assert len(out) == 3
    assert all(im.mode == "RGB" for im in out)


def test_load_document_pdf_page_cap():
    out = load_document(_pdf_bytes(pages=15), max_pages=10)
    assert len(out) == 10


def test_enhance_returns_same_size_rgb():
    out = enhance(Image.new("RGB", (120, 90), "gray"))
    assert out.mode == "RGB"
    assert out.size == (120, 90)
