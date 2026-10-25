import io

import pytest

from app.ocr import storage


class _FakeBody:
    def __init__(self, data: bytes):
        self._b = io.BytesIO(data)

    def read(self) -> bytes:
        return self._b.read()


def test_fetch_object_returns_bytes(monkeypatch):
    class _FakeClient:
        def get_object(self, Bucket, Key):
            assert Key == "anaemia/r1.webp"
            return {"Body": _FakeBody(b"IMG")}

    monkeypatch.setattr(storage, "_client", lambda: _FakeClient())
    assert storage.fetch_object("anaemia/r1.webp") == b"IMG"


def test_fetch_object_missing_raises_storage_error(monkeypatch):
    class _FakeClient:
        def get_object(self, Bucket, Key):
            raise RuntimeError("NoSuchKey")

    monkeypatch.setattr(storage, "_client", lambda: _FakeClient())
    with pytest.raises(storage.StorageError):
        storage.fetch_object("missing.webp")
