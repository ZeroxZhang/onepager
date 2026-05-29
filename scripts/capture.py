#!/usr/bin/env python3
"""
Onepager — HTML to PNG capture script.

Uses Playwright to render an HTML file and capture it as a high-quality PNG image.
Supports fixed dimensions and auto-height (full-page) modes.

Usage:
    python3 capture.py <input.html> --output <output.png> --width <px> [--height <px|auto>] [--scale <factor>] [--timeout <ms>]

Examples:
    # Portrait (auto height)
    python3 capture.py onepage.html --output onepage.png --width 800 --height auto

    # Landscape (fixed)
    python3 capture.py onepage.html --output onepage.png --width 1920 --height 1080

    # Square (fixed)
    python3 capture.py onepage.html --output onepage.png --width 1080 --height 1080

    # High-DPI (2x scale)
    python3 capture.py onepage.html --output onepage.png --width 800 --height auto --scale 2
"""

import argparse
import asyncio
import os
import sys


async def capture(input_path: str, output_path: str, width: int, height: str, scale: float, timeout: int):
    """Render HTML and capture screenshot."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright is not installed.")
        print("Run: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    abs_input = os.path.abspath(input_path)
    if not os.path.exists(abs_input):
        print(f"ERROR: Input file not found: {abs_input}")
        sys.exit(1)

    actual_height = "unknown"
    file_url = f"file://{abs_input}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": width, "height": 800},
            device_scale_factor=scale,
        )

        # Navigate with explicit timeout
        try:
            await page.goto(file_url, wait_until="networkidle", timeout=timeout)
        except Exception as e:
            print(f"WARN: Page navigation timeout or error: {e}")
            print("      Attempting to proceed with partial render...")

        # Wait for fonts to finish loading (use document.fonts.ready when available)
        try:
            await page.evaluate("document.fonts?.ready")
        except Exception:
            pass  # document.fonts may not be available in all contexts
        # Short buffer for final paint
        await page.wait_for_timeout(500)

        if height == "auto":
            # Full-page screenshot (auto height)
            await page.screenshot(
                path=output_path,
                full_page=True,
                type="png",
            )
            # Get actual page height for reporting
            actual_height = await page.evaluate("document.documentElement.scrollHeight")
        else:
            # Fixed viewport screenshot
            h = int(height)
            await page.set_viewport_size({"width": width, "height": h})
            # Brief re-render after viewport resize
            await page.wait_for_timeout(300)
            await page.screenshot(
                path=output_path,
                full_page=False,
                clip={"x": 0, "y": 0, "width": width, "height": h},
                type="png",
            )

        await browser.close()

    print(f"OK: Screenshot saved to {output_path}")
    if height == "auto":
        print(f"    Dimensions: {width}px x {actual_height}px (scale: {scale}x, auto height)")
    else:
        print(f"    Dimensions: {width}px x {height}px (scale: {scale}x)")


def main():
    parser = argparse.ArgumentParser(description="Capture HTML as PNG image.")
    parser.add_argument("input", help="Path to input HTML file")
    parser.add_argument("--output", "-o", required=True, help="Path to output PNG file")
    parser.add_argument("--width", "-w", type=int, required=True, help="Viewport width in pixels")
    parser.add_argument("--height", default="auto", help="Viewport height in pixels, or 'auto' for full page")
    parser.add_argument("--scale", "-s", type=float, default=2.0, help="Device scale factor (default: 2.0 for Retina)")
    parser.add_argument("--timeout", "-t", type=int, default=30000, help="Navigation timeout in ms (default: 30000)")
    args = parser.parse_args()

    asyncio.run(capture(args.input, args.output, args.width, args.height, args.scale, args.timeout))


if __name__ == "__main__":
    main()
