"""Verify BLIK bank confirmation uploads (forensics + OCR/PDF text)."""
from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .verify_forensics import analyze_document_integrity, validate_bank_document_text

log = logging.getLogger(__name__)

_ocr_available: bool | None = None


def ocr_available() -> bool:
    global _ocr_available
    if _ocr_available is not None:
        return _ocr_available
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        _ocr_available = True
    except Exception:
        _ocr_available = False
    return _ocr_available


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 9:
        return digits[-9:]
    return digits


def _extract_amounts(text: str) -> list[Decimal]:
    amounts: list[Decimal] = []
    for m in re.finditer(r"(\d{1,6})[,.](\d{2})\b", text):
        try:
            amounts.append(Decimal(f"{m.group(1)}.{m.group(2)}"))
        except InvalidOperation:
            continue
    for m in re.finditer(r"\b(\d{2,6})\s*(?:PLN|zł|zl)\b", text, re.I):
        try:
            amounts.append(Decimal(m.group(1)))
        except InvalidOperation:
            continue
    return amounts


def _read_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:5]:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
    except Exception:
        log.debug("pdf text extract failed for %s", path, exc_info=True)
    return "\n".join(parts)


def _preprocess_for_ocr(img):
    from PIL import ImageEnhance, ImageFilter, ImageOps

    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Contrast(gray).enhance(1.6)
    gray = ImageEnhance.Sharpness(gray).enhance(1.4)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def _read_image_text(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        log.warning("pytesseract/Pillow not installed — OCR disabled")
        return ""
    try:
        with Image.open(path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            prepped = _preprocess_for_ocr(img)
            cfg = "--psm 6 -c preserve_interword_spaces=1"
            return pytesseract.image_to_string(prepped, lang="pol+eng", config=cfg) or ""
    except pytesseract.TesseractNotFoundError:
        log.warning("tesseract binary not found — install tesseract-ocr (pol+eng)")
        return ""
    except Exception:
        log.debug("OCR failed for %s", path, exc_info=True)
        return ""


def _ocr_pdf_scanned(path: Path) -> str:
    from .verify_forensics import render_pdf_first_page

    rendered = render_pdf_first_page(path)
    if rendered is None:
        return ""
    try:
        import pytesseract
        from io import BytesIO

        buf = BytesIO()
        rendered.save(buf, format="PNG")
        buf.seek(0)
        from PIL import Image

        with Image.open(buf) as img:
            prepped = _preprocess_for_ocr(img)
            return pytesseract.image_to_string(prepped, lang="pol+eng", config="--psm 6") or ""
    except Exception:
        log.debug("PDF OCR failed for %s", path, exc_info=True)
        return ""


def extract_text_from_file(path: Path, content_type: str | None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf" or (content_type or "").startswith("application/pdf"):
        text = _read_pdf_text(path)
        if len(text.strip()) < 30:
            ocr = _ocr_pdf_scanned(path)
            if len(ocr.strip()) > len(text.strip()):
                return ocr
        return text
    if suffix in (".png", ".jpg", ".jpeg", ".webp") or (content_type or "").startswith("image/"):
        return _read_image_text(path)
    return ""


def verify_blik_proof(
    path: Path,
    *,
    expected_amount: Decimal,
    expected_phone: str | None,
    content_type: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Returns {ok, reason, extractedText (truncated), checks}.
    strict=False allows approval when OCR unavailable but file passes forensics.
    """
    if not path.exists() or path.stat().st_size < 1024:
        return {"ok": False, "reason": "file_too_small", "checks": {}}

    forensics = analyze_document_integrity(path, content_type)
    checks: dict[str, Any] = {"forensics": forensics}

    if forensics.get("rejectReason"):
        return {
            "ok": False,
            "reason": forensics["rejectReason"],
            "checks": checks,
            "extractedText": "",
        }

    checks["ocrAvailable"] = ocr_available()
    text = extract_text_from_file(path, content_type)
    checks["hasText"] = bool(text.strip())
    doc_validation = validate_bank_document_text(text)
    checks["document"] = doc_validation

    suffix = path.suffix.lower()
    is_image = suffix in (".png", ".jpg", ".jpeg", ".webp") or (
        (content_type or "").startswith("image/")
    )
    if strict and is_image and not checks["ocrAvailable"]:
        return {
            "ok": False,
            "reason": "ocr_unavailable",
            "checks": checks,
            "extractedText": "",
        }

    if not text.strip():
        if not strict:
            if forensics.get("authenticityOk"):
                return {
                    "ok": True,
                    "reason": "accepted_non_strict",
                    "checks": {**checks, "ocr": "skipped"},
                    "extractedText": "",
                }
            return {
                "ok": False,
                "reason": "missing_authenticity_markers",
                "checks": checks,
                "extractedText": "",
            }
        return {"ok": False, "reason": "no_text_extracted", "checks": checks}

    if strict and not doc_validation.get("documentKeywordsOk"):
        return {
            "ok": False,
            "reason": "not_bank_document",
            "checks": checks,
            "extractedText": text[:2000],
        }

    if strict and not doc_validation.get("bankMarkerOk"):
        return {
            "ok": False,
            "reason": "not_bank_document",
            "checks": checks,
            "extractedText": text[:2000],
        }

    amounts = _extract_amounts(text)
    amount_ok = any(abs(a - expected_amount) <= Decimal("0.02") for a in amounts)
    checks["amountsFound"] = [str(a) for a in amounts[:10]]
    checks["amountMatch"] = amount_ok

    phone_ok = True
    if expected_phone:
        norm = _normalize_phone(expected_phone)
        text_digits = re.sub(r"\D", "", text)
        phone_ok = norm in text_digits if norm else True
        checks["phoneMatch"] = phone_ok

    authenticity_ok = bool(forensics.get("authenticityOk")) or bool(
        doc_validation.get("bankMarkerOk")
    )
    checks["authenticityOk"] = authenticity_ok

    if strict and not authenticity_ok:
        return {
            "ok": False,
            "reason": "missing_authenticity_markers",
            "checks": checks,
            "extractedText": text[:2000],
        }

    ok = amount_ok and phone_ok
    return {
        "ok": ok,
        "reason": "verified" if ok else "amount_or_phone_mismatch",
        "checks": checks,
        "extractedText": text[:2000],
    }
