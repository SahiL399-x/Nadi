from functools import lru_cache

# PaddleOCR default pipeline models (PP-OCRv6 det+rec as of paddleocr 3.7.0).
# CPU-runnable for the deferred production host.
MODEL_VERSION = "paddleocr-3.7.0-default"


@lru_cache(maxsize=1)
def _engine():
    # Imported lazily so unit tests (which inject a fake ocr_fn) never load Paddle.
    #
    # Verified empirically against the installed paddleocr==3.7.0 /
    # paddlepaddle==3.2.0 (3.x replaced the 2.x `use_angle_cls`/`show_log`
    # constructor kwargs and the `.ocr()` call entirely). We disable the doc
    # orientation/unwarping and textline-orientation sub-models since lab
    # report scans are assumed upright; this keeps the pipeline lean.
    from paddleocr import PaddleOCR
    return PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def run_ocr(image) -> list[dict]:
    """Adapter: PaddleOCR 3.7.0 result -> list[OcrLine].

    3.x's `.predict(img)` returns a list of `OCRResult` (dict-like) objects,
    one per page/image. Each result exposes `rec_texts` (list[str]),
    `rec_scores` (list[float]), and `rec_boxes` (Nx4 ndarray of
    [x1, y1, x2, y2] axis-aligned boxes), all aligned by index — confirmed by
    introspecting a real prediction run in the running ml-service container.
    Everything downstream consumes the OcrLine shape and is version-independent.
    """
    import numpy as np
    results = _engine().predict(np.array(image))
    lines: list[dict] = []
    for page in results or []:
        texts = page.get("rec_texts") or []
        scores = page.get("rec_scores") or []
        boxes = page.get("rec_boxes")
        if boxes is None:
            continue
        for text, score, box in zip(texts, scores, boxes):
            x1, y1, x2, y2 = (int(v) for v in box)
            lines.append({
                "text": text,
                "box": [x1, y1, x2 - x1, y2 - y1],
                "conf": float(score),
            })
    return lines
