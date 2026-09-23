"""Read price + RSI off a MetaTrader screenshot and apply the same RSI
threshold rule this project already uses (see strategy/mt_screenshot_signal.py),
so you can run it side by side with the OANDA gold bot on a practice account
and see whether MetaTrader's feed produces a different picture than OANDA's.

Signal-only: this never places an order. It reads an image, prints a
long/short/none call, and logs it to logs/screenshot_signals.csv.

Setup (one-time):
  1. System OCR engine — not a Python package, install separately:
       Debian/Ubuntu:  sudo apt install tesseract-ocr
       Termux:         pkg install tesseract-ocr
  2. pip install -r requirements.txt   (pulls in pytesseract + Pillow)

Usage:
  Take a screenshot of MetaTrader (any OS screenshot tool), then:

    python3 mt_screenshot_reader.py path/to/screenshot.png

  Reading the whole image works if RSI and price are visible as plain text
  near "RSI" and the instrument's quote, but MetaTrader's layout varies a
  lot by theme/broker. For a reliable reading, crop each value's location
  once (find the pixel box in any image viewer) and pass it every time:

    python3 mt_screenshot_reader.py shot.png \\
        --price-region 1400,60,120,30 \\
        --rsi-region 1400,820,80,30

  Region format is "left,top,width,height" in pixels from the image's
  top-left corner.
"""

import argparse
import re
import sys

import pytesseract
from PIL import Image

from logs.screenshot_log import log_screenshot_signal
from strategy.mt_screenshot_signal import rsi_threshold_signal

_NUMBER_RE = re.compile(r"[-+]?\d{1,6}(?:\.\d{1,6})?")
# Skip an optional "(14)"-style period parameter right after the RSI label
# (common in MetaTrader indicator labels) so it isn't mistaken for the value.
_RSI_LABEL_RE = re.compile(r"RSI\s*(?:\(\s*\d+\s*\))?\D{0,15}?(\d{1,3}(?:\.\d{1,6})?)", re.IGNORECASE)


def _parse_region(spec: str) -> tuple[int, int, int, int]:
    parts = [int(p.strip()) for p in spec.split(",")]
    if len(parts) != 4:
        raise ValueError(f"--region must be 'left,top,width,height', got {spec!r}")
    left, top, width, height = parts
    return left, top, left + width, top + height


def _ocr(image: Image.Image, region: tuple[int, int, int, int] | None) -> str:
    crop = image.crop(region) if region else image
    return pytesseract.image_to_string(crop)


def extract_price(image: Image.Image, region: tuple[int, int, int, int] | None, price_min: float, price_max: float) -> float | None:
    text = _ocr(image, region)
    if region:
        # Dedicated crop: trust the first number found in it.
        match = _NUMBER_RE.search(text)
        return float(match.group()) if match else None
    # No crop given: scan the whole image's text for a number in the
    # instrument's plausible price range, to avoid picking up RSI, volume,
    # or timestamp digits instead.
    for match in _NUMBER_RE.finditer(text):
        value = float(match.group())
        if price_min <= value <= price_max:
            return value
    return None


def extract_rsi(image: Image.Image, region: tuple[int, int, int, int] | None) -> float | None:
    text = _ocr(image, region)
    if region:
        match = _NUMBER_RE.search(text)
        if match:
            return float(match.group())
        return None
    match = _RSI_LABEL_RE.search(text)
    return float(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Path to the MetaTrader screenshot")
    parser.add_argument("--price-region", help="'left,top,width,height' crop box around the price")
    parser.add_argument("--rsi-region", help="'left,top,width,height' crop box around the RSI value")
    parser.add_argument("--price-min", type=float, default=1000.0, help="Lowest plausible price, used only without --price-region (default: gold-range 1000)")
    parser.add_argument("--price-max", type=float, default=6000.0, help="Highest plausible price, used only without --price-region (default: gold-range 6000)")
    parser.add_argument("--rsi-overbought", type=float, default=70.0)
    parser.add_argument("--rsi-oversold", type=float, default=30.0)
    parser.add_argument("--note", default="", help="Free-text note to store alongside this read (e.g. 'vs OANDA stophunt: long')")
    args = parser.parse_args()

    image = Image.open(args.image)
    price_region = _parse_region(args.price_region) if args.price_region else None
    rsi_region = _parse_region(args.rsi_region) if args.rsi_region else None

    price = extract_price(image, price_region, args.price_min, args.price_max)
    rsi = extract_rsi(image, rsi_region)

    signal = rsi_threshold_signal(rsi, args.rsi_overbought, args.rsi_oversold) if rsi is not None else None

    print(f"price: {price if price is not None else 'not found'}")
    print(f"rsi:   {rsi if rsi is not None else 'not found'}")
    print(f"signal: {signal or 'none'}")
    if rsi is None:
        print("\nCouldn't read RSI from this image — try --rsi-region with a tight crop around just the RSI number.", file=sys.stderr)
    if price is None:
        print("Couldn't read price from this image — try --price-region, or widen --price-min/--price-max.", file=sys.stderr)

    log_screenshot_signal(args.image, price, rsi, signal, args.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
