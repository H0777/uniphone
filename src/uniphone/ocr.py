"""OCR backends: Apple Vision on macOS, RapidOCR everywhere else.

Only needed for drivers without a real UI tree (iOS mirroring). Android gets
its element tree from uiautomator, so OCR is optional there.
"""
import struct, sys

_backend = None
_engine = None


def image_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
    if head[:4] != b"\x89PNG":
        raise RuntimeError(f"not a PNG: {path}")
    return struct.unpack(">II", head[16:24])


def backend():
    global _backend
    if _backend:
        return _backend
    if sys.platform == "darwin":
        try:
            import Vision  # noqa: F401
            _backend = "vision"
            return _backend
        except ImportError:
            pass
    try:
        import rapidocr_onnxruntime  # noqa: F401
        _backend = "rapidocr"
        return _backend
    except ImportError:
        pass
    raise RuntimeError(
        "No OCR backend. macOS: pip install pyobjc-framework-Vision - "
        "anywhere: pip install rapidocr-onnxruntime")


def recognize(path, bounds):
    """[{text, confidence, x, y, w, h}] - (x, y) is the box center in driver
    coordinates (bounds space), ready for tap()."""
    b = backend()
    img_w, img_h = image_size(path)
    raw = _vision(path) if b == "vision" else _rapidocr(path)
    sx, sy = bounds["w"] / img_w, bounds["h"] / img_h
    out = []
    for text, conf, (px, py, pw, ph) in raw:
        out.append({
            "text": text,
            "confidence": round(float(conf), 3),
            "x": round(bounds["x"] + (px + pw / 2) * sx, 1),
            "y": round(bounds["y"] + (py + ph / 2) * sy, 1),
            "w": round(pw * sx, 1),
            "h": round(ph * sy, 1),
        })
    return out


def _vision(path):
    """[(text, confidence, (x, y, w, h) px, top-left origin)] via Vision."""
    import Vision
    from Foundation import NSURL
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(
        NSURL.fileURLWithPath_(path), {})
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Vision OCR failed: {err}")
    img_w, img_h = image_size(path)
    out = []
    for obs in request.results() or []:
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        bb = obs.boundingBox()
        px = bb.origin.x * img_w
        py = (1.0 - bb.origin.y - bb.size.height) * img_h  # bottom-left -> top-left
        out.append((str(cand[0].string()), float(cand[0].confidence()),
                    (px, py, bb.size.width * img_w, bb.size.height * img_h)))
    return out


def _rapidocr(path):
    global _engine
    from rapidocr_onnxruntime import RapidOCR
    if _engine is None:
        _engine = RapidOCR()
    result, _ = _engine(path)
    out = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        out.append((text, conf,
                    (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))))
    return out
