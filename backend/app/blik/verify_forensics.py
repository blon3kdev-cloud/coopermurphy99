"""Forensic checks for BLIK bank confirmation uploads (anti-screenshot, tampering, authenticity)."""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

# Polish bank names / brands often visible on official confirmations
_BANK_NAMES = (
    "mbank",
    "m bank",
    "pko",
    "bp",
    "ing",
    "santander",
    "millennium",
    "alior",
    "pekao",
    "bnp",
    "paribas",
    "credit agricole",
    "bos",
    "nest",
    "velobank",
    "citibank",
    "getin",
)

_DOCUMENT_KEYWORDS = (
    "blik",
    "przelew",
    "potwierdz",
    "transakcj",
    "operacj",
    "kwot",
    "odbiorc",
    "nadawc",
    "rachun",
    "numer",
    "data",
    "pln",
    "zł",
    "zl",
    "potwierdzenie",
    "wypłat",
    "wpłat",
)

_EDITING_SOFTWARE = (
    "photoshop",
    "adobe",
    "gimp",
    "canva",
    "paint.net",
    "affinity",
    "pixelmator",
    "snapseed",
    "lightroom",
)

_SCREENSHOT_SOFTWARE = (
    "screenshot",
    "screen shot",
    "screencapture",
    "snipping",
    "ios",
    "android",
    "samsung capture",
    "miui",
    "one ui",
)


def _load_image(path: Path):
    from PIL import Image

    with Image.open(path) as img:
        return img.convert("RGB")


def render_pdf_first_page(path: Path):
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    try:
        pdf = pdfium.PdfDocument(str(path))
        if len(pdf) < 1:
            return None
        page = pdf[0]
        bitmap = page.render(scale=2)
        pil = bitmap.to_pil()
        pdf.close()
        return pil.convert("RGB")
    except Exception:
        return None


def _exif_report(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"present": False, "software": "", "make": "", "model": "", "flags": []}
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(path) as img:
            raw = img.getexif()
            if not raw:
                return out
            out["present"] = True
            decoded = {TAGS.get(k, str(k)): v for k, v in raw.items() if v is not None}
            for key in ("Software", "ProcessingSoftware", "HostComputer", "Artist"):
                val = decoded.get(key)
                if val:
                    out["software"] = f"{out['software']} {val}".strip().lower()
            out["make"] = str(decoded.get("Make", "") or "").lower()
            out["model"] = str(decoded.get("Model", "") or "").lower()
            for tag, val in decoded.items():
                blob = f"{tag} {val}".lower()
                for marker in _EDITING_SOFTWARE:
                    if marker in blob:
                        out["flags"].append(f"exif_editing:{marker}")
                for marker in _SCREENSHOT_SOFTWARE:
                    if marker in blob:
                        out["flags"].append(f"exif_screenshot:{marker}")
    except Exception:
        pass
    return out


def _status_bar_likely(img) -> bool:
    """Phone screenshots often have a flat, high-contrast status bar in the top ~3%."""
    w, h = img.size
    if h < 400:
        return False
    band = max(8, int(h * 0.035))
    crop = img.crop((0, 0, w, band))
    pixels = list(crop.getdata())
    if not pixels:
        return False
    # Flat bar: very low color variance across the row
    rs = [p[0] for p in pixels]
    gs = [p[1] for p in pixels]
    bs = [p[2] for p in pixels]
    spread = (max(rs) - min(rs)) + (max(gs) - min(gs)) + (max(bs) - min(bs))
    if spread > 40:
        return False
    avg = sum(sum(p) for p in pixels) / (len(pixels) * 3)
    # Mobile status bars: dark chrome or flat tinted bar — not white paper margins.
    if avg < 55:
        return True
    return spread < 18 and 70 < avg < 175


def _phone_aspect_likely(w: int, h: int) -> bool:
    if w <= 0 or h <= 0:
        return False
    short, long = sorted((w, h))
    ratio = long / short
    # Common phone portrait ratios (~2.0–2.3)
    return 1.95 <= ratio <= 2.35 and long >= 700


def _ela_score(img, *, is_jpeg_source: bool) -> float:
    """Error Level Analysis on JPEG — not applied to lossless PNG uploads."""
    if not is_jpeg_source:
        return 0.0
    from PIL import Image, ImageChops, ImageFilter

    buf = BytesIO()
    work = img.copy()
    if work.mode != "RGB":
        work = work.convert("RGB")
    work.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    diff = ImageChops.difference(work, recompressed)
    diff = diff.filter(ImageFilter.SHARPEN)
    hist = diff.histogram()
    total = sum(i * c for i, c in enumerate(hist))
    count = sum(hist) or 1
    mean = total / count
    return min(100.0, mean * 1.4)


def _regional_noise_variance(img) -> dict[str, float]:
    try:
        import numpy as np
    except ImportError:
        return {}
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = arr.shape
    if h < 80 or w < 80:
        return {}

    def block_var(y0: int, y1: int) -> float:
        region = arr[y0:y1, :]
        if region.size < 100:
            return 0.0
        # 8x8 block std dev average
        bh, bw = 8, 8
        vals: list[float] = []
        for y in range(0, region.shape[0] - bh, bh):
            for x in range(0, region.shape[1] - bw, bw):
                block = region[y : y + bh, x : x + bw]
                vals.append(float(block.std()))
        return sum(vals) / len(vals) if vals else 0.0

    top = block_var(0, h // 4)
    mid = block_var(h // 4, (3 * h) // 4)
    bottom = block_var((3 * h) // 4, h)
    return {"top": top, "mid": mid, "bottom": bottom}


def _signature_region_score(img) -> dict[str, Any]:
    """
    Heuristic: official docs often have logo/stamp/signature in header or footer
    with more ink/edges than a plain screenshot of app UI text.
    """
    w, h = img.size
    if h < 120:
        return {"present": False, "confidence": 0.0}

    noise = _regional_noise_variance(img)
    if not noise:
        return {"present": False, "confidence": 0.0, "noise": noise}

    bottom_boost = noise["bottom"] > max(noise["mid"] * 1.15, 6.0)
    top_boost = noise["top"] > max(noise["mid"] * 1.1, 5.5)
    # Footer/header ink vs flat middle (app lists)
    confidence = 0.0
    if bottom_boost:
        confidence += 0.55
    if top_boost:
        confidence += 0.35
    if noise["bottom"] + noise["top"] > noise["mid"] * 1.35:
        confidence += 0.1
    confidence = min(1.0, confidence)
    return {
        "present": confidence >= 0.4,
        "confidence": round(confidence, 3),
        "noise": {k: round(v, 2) for k, v in noise.items()},
    }


def _pdf_metadata_flags(path: Path) -> list[str]:
    flags: list[str] = []
    try:
        import pdfplumber
    except ImportError:
        return flags
    try:
        with pdfplumber.open(path) as pdf:
            meta = pdf.metadata or {}
            blob = " ".join(str(v) for v in meta.values() if v).lower()
            for marker in _EDITING_SOFTWARE:
                if marker in blob:
                    flags.append(f"pdf_meta_editing:{marker}")
            creator = str(meta.get("Creator", "") or "").lower()
            producer = str(meta.get("Producer", "") or "").lower()
            if "print to pdf" in creator or "microsoft" in producer:
                flags.append("pdf_print_to_pdf")
    except Exception:
        pass
    return flags


def _pdf_text_ratio(path: Path) -> float:
    try:
        import pdfplumber
    except ImportError:
        return 0.0
    try:
        with pdfplumber.open(path) as pdf:
            if not pdf.pages:
                return 0.0
            page = pdf.pages[0]
            text = (page.extract_text() or "").strip()
            if len(text) >= 40:
                return 1.0
            if page.images:
                return 0.2
            return 0.0
    except Exception:
        return 0.0


def analyze_document_integrity(path: Path, content_type: str | None = None) -> dict[str, Any]:
    """
    Returns forensic signals. Caller maps rejectReason when checks fail.
    """
    suffix = path.suffix.lower()
    is_pdf = suffix == ".pdf" or (content_type or "").startswith("application/pdf")
    flags: list[str] = []
    screenshot_signals: list[str] = []

    img = None
    if is_pdf:
        flags.extend(_pdf_metadata_flags(path))
        if _pdf_text_ratio(path) < 0.5:
            img = render_pdf_first_page(path)
            if img is None:
                flags.append("pdf_no_render")
    else:
        try:
            img = _load_image(path)
        except Exception:
            return {
                "rejectReason": "unreadable_image",
                "screenshotLikely": True,
                "authenticityOk": False,
                "flags": ["unreadable_image"],
            }

    exif: dict[str, Any] = {}
    if not is_pdf and path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        exif = _exif_report(path)
        flags.extend(exif.get("flags", []))
        if not exif.get("present") and path.suffix.lower() in (".jpg", ".jpeg"):
            screenshot_signals.append("missing_camera_exif")

    ela = 0.0
    signature: dict[str, Any] = {"present": False, "confidence": 0.0}
    status_bar = False
    phone_aspect = False

    is_jpeg_source = path.suffix.lower() in (".jpg", ".jpeg") and not is_pdf

    if img is not None:
        w, h = img.size
        ela = round(_ela_score(img, is_jpeg_source=is_jpeg_source), 2)
        signature = _signature_region_score(img)
        status_bar = _status_bar_likely(img)
        phone_aspect = _phone_aspect_likely(w, h)
        if status_bar:
            screenshot_signals.append("status_bar_strip")
        if phone_aspect and not is_pdf:
            screenshot_signals.append("phone_display_aspect")

    if is_jpeg_source and ela >= 22.0:
        flags.append("high_ela_score")
    if is_jpeg_source and ela >= 32.0:
        flags.append("severe_ela_score")

    exif_screenshot = any(f.startswith("exif_screenshot") for f in flags)
    # Avoid rejecting photos of paper confirmations (portrait + no EXIF is common).
    screenshot_likely = (
        exif_screenshot
        or status_bar
        or (status_bar and phone_aspect)
    )

    editing_likely = any("editing" in f for f in flags) or (is_jpeg_source and ela >= 32.0)
    authenticity_ok = signature.get("present", False) or (is_pdf and _pdf_text_ratio(path) >= 0.5)

    reject: str | None = None
    if screenshot_likely:
        reject = "screenshot_detected"
    elif editing_likely:
        reject = "document_edited"
    elif img is not None and not authenticity_ok:
        reject = "missing_authenticity_markers"

    return {
        "rejectReason": reject,
        "screenshotLikely": screenshot_likely,
        "editingLikely": editing_likely,
        "authenticityOk": authenticity_ok,
        "screenshotSignals": screenshot_signals,
        "flags": flags,
        "exif": exif,
        "elaScore": ela,
        "signature": signature,
        "statusBarLikely": status_bar,
        "phoneAspectLikely": phone_aspect,
        "isPdf": is_pdf,
    }


def validate_bank_document_text(text: str) -> dict[str, Any]:
    lower = (text or "").lower()
    doc_hits = [k for k in _DOCUMENT_KEYWORDS if k in lower]
    bank_hits = [b for b in _BANK_NAMES if b in lower]
    has_blik = "blik" in lower
    return {
        "documentKeywordHits": doc_hits[:12],
        "bankNamesFound": bank_hits[:5],
        "hasBlik": has_blik,
        "documentKeywordsOk": len(doc_hits) >= 3,
        "bankMarkerOk": len(bank_hits) >= 1 or has_blik,
    }
