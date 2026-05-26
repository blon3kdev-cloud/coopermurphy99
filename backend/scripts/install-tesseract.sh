#!/usr/bin/env sh
# Install Tesseract OCR for BLIK document verification (no Homebrew required).
set -e
cd "$(dirname "$0")/.."

echo "=== Python deps (Pillow, pytesseract, numpy) ==="
.venv/bin/pip install -q Pillow pytesseract numpy

if command -v tesseract >/dev/null 2>&1; then
  echo "Tesseract already installed: $(tesseract --version 2>&1 | head -1)"
  tesseract --list-langs 2>/dev/null | grep -q pol && echo "Polish (pol) language: OK" || echo "WARN: install tesseract-ocr-pol for Polish OCR"
  exit 0
fi

OS="$(uname -s)"
case "$OS" in
  Linux)
    if command -v apt-get >/dev/null 2>&1; then
      echo "=== Installing via apt (needs sudo) ==="
      sudo apt-get update
      sudo apt-get install -y tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y tesseract tesseract-langpack-pol
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --needed tesseract tesseract-data-pol tesseract-data-eng
    else
      echo "Install tesseract-ocr and Polish language pack using your distro package manager."
      exit 1
    fi
    ;;
  Darwin)
    echo "macOS without Homebrew:"
    echo "  1) MacPorts:  sudo port install tesseract +tesseract_pol"
    echo "  2) Or download UB Mannheim build:"
    echo "     https://github.com/UB-Mannheim/tesseract/wiki"
    echo "     Add the .app bundle bin folder to your PATH."
    echo ""
    echo "After install, run: tesseract --list-langs   (should list pol and eng)"
    exit 1
    ;;
  *)
    echo "Unsupported OS: $OS — install Tesseract manually."
    exit 1
    ;;
esac

echo "Done: $(tesseract --version 2>&1 | head -1)"
