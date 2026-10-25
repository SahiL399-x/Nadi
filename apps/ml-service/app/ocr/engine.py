from functools import lru_cache

# PP-OCRv5 lightweight (mobile) detection+recognition. GPU on the dev 3050,
# CPU-runnable for the deferred production host.
MODEL_VERSION = "paddleocr-ppocrv5-mobile"


@lru_cache(maxsize=1)
def _engine():
    # Imported lazily so unit tests (which inject a fake ocr_fn) never load Paddle.
    from paddleocr import PaddleOCR
    return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)


def run_ocr(image) -> list[dict]:
    """Adapter: PaddleOCR result -> list[OcrLine]. This is the single
    version-sensitive seam — confirm the call signature and result shape against
    the installed PaddleOCR version during the Task 7 smoke test and adjust here.
    Everything downstream consumes the OcrLine shape and is version-independent."""
    import numpy as np
    result = _engine().ocr(np.array(image), cls=True)
    lines: list[dict] = []
    for page in result or []:
        for entry in page or []:
            box, (text, conf) = entry[0], entry[1]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lines.append({
                "text": text,
                "box": [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))],
                "conf": float(conf),
            })
    return lines
