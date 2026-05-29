#!/usr/bin/env python3
"""
Onepager — Quality Check Script

Performs automated quality checks on generated HTML files before screenshot.
Checks for: structure, BigNumber presence, blue-purple tones, emoji usage,
color count, shadow abuse, layout issues, contrast ratios, and size-specific
layout rules (A2/A3/A4 fixed-height canvas).

Usage:
    python3 quality_check.py <input.html> [--style B?] [--size A?] [--no-bignum]

Exit codes:
    0 = PASS
    1 = WARN (warnings present but no errors)
    2 = FAIL (errors present)
"""

import argparse
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path


class HTMLChecker(HTMLParser):
    """Parse HTML to extract structure, styles, and text content."""

    def __init__(self):
        super().__init__()
        self.has_charset = False
        self.has_font_import = False
        self.has_h1 = False
        self.has_footer = False
        self.has_bignum = False
        self.style_blocks = []
        self.text_content = []
        self.color_values = []  # list of (raw_str, rgb_tuple)
        self.box_shadows = []
        self.border_radii = []
        self.flex_ones = []
        self.grid_template_rows_missing = []
        self.absolute_positions = []
        self.current_tag = None
        self.in_style = False
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)

        if tag == "meta":
            if attrs_dict.get("charset", "").lower() == "utf-8":
                self.has_charset = True

        if tag == "style":
            self.in_style = True

        if tag == "script":
            self.in_script = True

        if tag == "h1":
            self.has_h1 = True

        # Check for footer class
        if tag in ("div", "footer", "section"):
            cls = attrs_dict.get("class", "")
            if "footer" in cls.split():
                self.has_footer = True
            if "bignum" in cls or "bignum-item" in cls or "bignum-value" in cls:
                self.has_bignum = True

        # Check for font loading
        if tag == "link":
            href = attrs_dict.get("href", "")
            if "fonts.googleapis.com" in href or "fonts.gstatic.com" in href:
                self.has_font_import = True
        if tag == "style":
            self.has_font_import = True  # Will check content later

        # Check inline styles for issues
        style = attrs_dict.get("style", "")
        if style:
            self._check_inline_style(style, tag)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        self.current_tag = None

    def handle_data(self, data):
        if self.in_style:
            self.style_blocks.append(data)
            self._extract_css_issues(data)
        elif not self.in_script:
            self.text_content.append(data)

    def _check_inline_style(self, style, tag=""):
        """Check inline styles for common issues."""
        s = style.replace(" ", "")
        if "flex:1" in s:
            self.flex_ones.append(f"<{tag}> inline style: {style[:60]}")
        if "position:absolute" in s:
            self.absolute_positions.append(f"<{tag}> inline style: {style[:60]}")

    def _extract_css_issues(self, css):
        """Extract colors, shadows, and layout issues from CSS blocks."""
        # Extract color values (store both raw string and parsed RGB)
        color_patterns = [
            r'#([0-9a-fA-F]{3,8})',
            r'rgb\((\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?)\)',
            r'rgba\((\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*)\)',
            r'hsl\((\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(?:,\s*[\d.]+\s*)?)\)',
            r'hsla\((\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*,\s*[\d.]+\s*)\)',
        ]
        for pattern in color_patterns:
            for match in re.finditer(pattern, css):
                raw = match.group(0)
                rgb = parse_color(raw)
                self.color_values.append((raw, rgb))

        # Extract box-shadows
        shadow_pattern = r'box-shadow\s*:\s*([^;]+)'
        for match in re.finditer(shadow_pattern, css, re.IGNORECASE):
            self.box_shadows.append(match.group(1).strip())

        # Extract border-radius values
        radius_pattern = r'border-radius\s*:\s*([^;]+)'
        for match in re.finditer(radius_pattern, css, re.IGNORECASE):
            self.border_radii.append(match.group(1).strip())

        # Check for flex: 1 in CSS
        flex_pattern = r'flex\s*:\s*1\b'
        for match in re.finditer(flex_pattern, css, re.IGNORECASE):
            start = max(0, match.start() - 100)
            context = css[start:match.start() + 20]
            self.flex_ones.append(f"CSS block: ...{context}...")

        # Check for grid without grid-template-rows in fixed-height contexts
        grid_pattern = r'display\s*:\s*grid'
        rows_pattern = r'grid-template-rows'
        if re.search(grid_pattern, css, re.IGNORECASE):
            if not re.search(rows_pattern, css, re.IGNORECASE):
                # Flag if there's any fixed-height context
                if re.search(r'height\s*:\s*(1080|1440)px', css):
                    self.grid_template_rows_missing.append(
                        "Grid layout without explicit grid-template-rows in fixed-height context"
                    )

        # Check for font imports in style blocks
        if 'fonts.googleapis.com' in css or 'fonts.gstatic.com' in css:
            self.has_font_import = True


def parse_color(color_str):
    """Convert color string to RGB tuple. Returns None if unparseable."""
    color_str = color_str.strip().lower()

    # Hex
    if color_str.startswith('#'):
        h = color_str[1:]
        if len(h) == 3:
            r, g, b = int(h[0]*2, 16), int(h[1]*2, 16), int(h[2]*2, 16)
            return (r, g, b)
        elif len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b)
        elif len(h) == 8:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b)
        return None

    # rgb/rgba
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # hsl/hsla
    m = re.match(r'hsla?\((\d+)', color_str)
    if m:
        h = int(m.group(1))
        # Approximate hue to RGB for checking purposes
        # Blue-purple range: 240-280
        if 240 <= h <= 280:
            return (100, 100, 200)  # Mark as blue-ish
        return (128, 128, 128)

    return None


def is_blue_purple(r, g, b):
    """Check if a color falls in the blue-purple range (the 'AI look')."""
    if r is None or g is None or b is None:
        return False

    max_val = max(r, g, b)

    # Blue: B is significantly higher than R and G
    if b > r + 30 and b > g + 30:
        if 200 <= max_val <= 255:
            return True

    # Purple detection: R and B both high, G is lower
    if r > 100 and b > 100 and g < min(r, b) - 20:
        if max_val > 150:
            return True

    # Specific known AI gradient colors
    known_ai_colors = [
        (99, 102, 241),   # #6366f1 (indigo)
        (139, 92, 246),   # #8b5cf6 (violet)
        (124, 58, 237),   # #7c3aed (purple)
    ]

    for kr, kg, kb in known_ai_colors:
        dist = ((r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2) ** 0.5
        if dist < 40:
            return True

    return False


def is_emoji(char):
    """Check if a character is an emoji using Unicode categories."""
    try:
        cat = unicodedata.category(char)
        # So = Symbol, Other (includes most emoji)
        # Sk = Symbol, Modifier
        if cat == 'So' or cat == 'Sk':
            return True
    except (ValueError, TypeError):
        pass

    # Additional ranges not covered by category
    code = ord(char)
    if 0x1F600 <= code <= 0x1F64F:  # Emoticons
        return True
    if 0x1F300 <= code <= 0x1F5FF:  # Misc Symbols and Pictographs
        return True
    if 0x1F680 <= code <= 0x1F6FF:  # Transport and Map
        return True
    if 0x1F1E6 <= code <= 0x1F1FF:  # Flags
        return True
    if 0x1F900 <= code <= 0x1F9FF:  # Supplemental Symbols
        return True
    if 0x1FA00 <= code <= 0x1FA6F:  # Chess, etc.
        return True
    if 0x1FA70 <= code <= 0x1FAFF:  # Symbols Extended-A
        return True
    if 0xFE00 <= code <= 0xFE0F:  # Variation Selectors
        return True
    if code == 0x200D:  # ZWJ
        return True
    if 0x1F3FB <= code <= 0x1F3FF:  # Skin tone modifiers
        return True
    return False


def check_contrast(bg_rgb, text_rgb):
    """Calculate WCAG contrast ratio. Returns ratio (1-21)."""
    def luminance(rgb):
        r, g, b = [x / 255.0 for x in rgb]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    L1 = luminance(text_rgb)
    L2 = luminance(bg_rgb)
    lighter = max(L1, L2)
    darker = min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)


def run_checks(html_path, style=None, size=None, no_bignum=False):
    """Run all quality checks on the HTML file."""
    path = Path(html_path)
    if not path.exists():
        print(f"ERROR: File not found: {html_path}")
        sys.exit(2)

    content = path.read_text(encoding='utf-8')
    checker = HTMLChecker()
    checker.feed(content)

    errors = []
    warnings = []
    passed = []

    # Normalize style/size
    style_norm = (style or "").strip().upper()
    size_norm = (size or "").strip().upper()
    is_b9 = style_norm == "B9"
    is_fixed_height = size_norm in ("A2", "A3", "A4")

    # ===== STRUCTURE CHECKS =====
    if checker.has_charset:
        passed.append("[STRUCTURE] UTF-8 charset declared")
    else:
        errors.append("[STRUCTURE] Missing <meta charset='UTF-8'>")

    if checker.has_font_import:
        passed.append("[STRUCTURE] Font loading configured")
    else:
        warnings.append("[STRUCTURE] No font import detected (may use system fonts only)")

    if checker.has_h1:
        passed.append("[STRUCTURE] Main heading (h1) present")
    else:
        errors.append("[STRUCTURE] Missing main heading (h1)")

    if checker.has_footer:
        passed.append("[STRUCTURE] Footer element present")
    else:
        warnings.append("[STRUCTURE] No footer element detected")

    # ===== BIGNUMBER CHECK =====
    if checker.has_bignum:
        passed.append("[BIGNUMBER] BigNumber module present")
    elif no_bignum:
        passed.append("[BIGNUMBER] BigNumber module skipped (user chose E2 — no BigNumber)")
    else:
        errors.append("[BIGNUMBER] Missing BigNumber module (.bignum-* class not found). Every OnePage MUST include at least one BigNumber data display.")

    # ===== STYLE NORMALIZATION =====
    # B9 (Google Native) intentionally uses Google blue and brand four-color
    B9_ALLOWED = {
        (66, 133, 244),   # #4285f4 brand blue
        (26, 115, 232),   # #1a73e8 primary blue
        (25, 103, 210),   # #1967d2 blue hover
        (234, 67, 53),    # #ea4335 brand red
        (251, 188, 4),    # #fbbc04 brand yellow
        (52, 168, 83),    # #34a853 brand green
        (138, 180, 248),  # #8ab4f8 I/O light blue
        (197, 138, 249),  # #c58af9 I/O purple accent
        (129, 201, 149),  # #81c995 I/O light green
    }

    def _is_b9_allowed(rgb):
        if rgb is None:
            return False
        for ar, ag, ab in B9_ALLOWED:
            if abs(rgb[0] - ar) + abs(rgb[1] - ag) + abs(rgb[2] - ab) <= 12:
                return True
        return False

    # ===== EMOJI CHECK =====
    full_text = ''.join(checker.text_content)
    emojis_found = []
    for i, char in enumerate(full_text):
        if is_emoji(char):
            start = max(0, i - 15)
            end = min(len(full_text), i + 16)
            context = full_text[start:end].replace('\n', ' ')
            emojis_found.append(f"'{char}' in: ...{context}...")

    if not emojis_found:
        passed.append("[EMOJI] No emoji characters detected")
    else:
        warnings.append(f"[EMOJI] Found {len(emojis_found)} emoji character(s). Replace with SVG icons:")
        for e in emojis_found[:5]:
            warnings.append(f"  - {e}")
        if len(emojis_found) > 5:
            warnings.append(f"  ... and {len(emojis_found) - 5} more")

    # ===== COLOR CHECKS =====
    # B7 数据新闻 uses #1e3a5f (deep navy) and #9f1239 (rust red)
    b7_allowed_colors = {
        (30, 58, 95),    # #1e3a5f
        (159, 18, 57),   # #9f1239
    }

    # Normalize colors: deduplicate by RGB tuple
    seen_rgb = set()
    unique_colors_raw = []
    for raw, rgb in checker.color_values:
        if rgb is not None:
            if rgb not in seen_rgb:
                seen_rgb.add(rgb)
                unique_colors_raw.append(raw)

    bp_colors = []
    for raw, rgb in checker.color_values:
        if rgb and is_blue_purple(*rgb):
            if style_norm == "B7" and rgb in b7_allowed_colors:
                continue
            if is_b9 and _is_b9_allowed(rgb):
                continue
            bp_colors.append(raw)

    # Deduplicate blue-purple warnings
    bp_colors = list(dict.fromkeys(bp_colors))

    if not bp_colors:
        if is_b9:
            passed.append("[COLOR] No blue-purple tones detected (Google brand colors allowed in B9)")
        else:
            passed.append("[COLOR] No blue-purple tones detected")
    else:
        warnings.append(f"[COLOR] Found {len(bp_colors)} blue-purple color value(s). Review to ensure they fit the design philosophy:")
        for c in bp_colors[:8]:
            warnings.append(f"  - {c}")
        if len(bp_colors) > 8:
            warnings.append(f"  ... and {len(bp_colors) - 8} more")

    # Color count (deduplicated by RGB)
    unique_color_count = len(seen_rgb)
    if is_b9:
        if unique_color_count <= 12:
            passed.append(f"[COLOR] Color palette is restrained for B9 Google Native ({unique_color_count} unique colors)")
        elif unique_color_count <= 16:
            warnings.append(f"[COLOR] B9 palette has {unique_color_count} unique colors. Brand four-color + neutrals is expected, but consider keeping <=12.")
        else:
            errors.append(f"[COLOR] Too many colors ({unique_color_count} unique) even for B9. Keep to Google brand four-color + neutrals + single blue CTA.")
    elif unique_color_count <= 7:
        warnings.append(f"[COLOR] Color palette has {unique_color_count} unique colors. Consider reducing to <=7 for visual consistency.")
    else:
        errors.append(f"[COLOR] Too many colors ({unique_color_count} unique). Limit to 3 main + 2 neutral colors maximum.")

    # ===== SHADOW CHECKS =====
    glow_shadows = []
    for shadow in checker.box_shadows:
        if re.search(r'\d{2,}px.*rgba?\([^)]*\)', shadow) or '0 0' in shadow:
            glow_shadows.append(shadow)

    if not glow_shadows:
        passed.append("[SHADOW] No glow-like shadows detected")
    else:
        warnings.append(f"[SHADOW] Found {len(glow_shadows)} potential glow shadow(s). Avoid 'box-shadow: 0 0 30px ...' patterns:")
        for s in glow_shadows[:3]:
            warnings.append(f"  - {s[:80]}")

    # ===== LAYOUT CHECKS =====
    # Fixed-height canvas checks (A2/A3/A4)
    if is_fixed_height:
        if checker.flex_ones:
            errors.append(f"[LAYOUT-FIXED] Found {len(checker.flex_ones)} use(s) of 'flex: 1' in {size_norm} fixed-height canvas. This causes layout issues:")
            for f in checker.flex_ones[:3]:
                errors.append(f"  - {f[:80]}")
        else:
            passed.append(f"[LAYOUT-FIXED] No 'flex: 1' usage in {size_norm} (correct)")

        if checker.grid_template_rows_missing:
            for msg in checker.grid_template_rows_missing:
                errors.append(f"[LAYOUT-FIXED] {msg}")
        else:
            passed.append(f"[LAYOUT-FIXED] Grid layouts properly configured for {size_norm}")

        # Check for grid-template-rows in the page-level CSS
        has_page_grid_rows = False
        for css in checker.style_blocks:
            if re.search(r'grid-template-rows', css):
                has_page_grid_rows = True
                break
        if has_page_grid_rows:
            passed.append(f"[LAYOUT-FIXED] grid-template-rows found in {size_norm} layout")
        else:
            warnings.append(f"[LAYOUT-FIXED] No grid-template-rows detected in {size_norm}. Fixed-height canvases MUST declare explicit row heights.")
    else:
        # A1: flex:1 is a warning, not an error
        if checker.flex_ones:
            warnings.append(f"[LAYOUT] Found {len(checker.flex_ones)} use(s) of 'flex: 1'. In fixed-height canvases (A2/A3/A4), this can cause layout issues:")
            for f in checker.flex_ones[:3]:
                warnings.append(f"  - {f[:80]}")
        else:
            passed.append("[LAYOUT] No 'flex: 1' usage detected")

        if checker.grid_template_rows_missing:
            for msg in checker.grid_template_rows_missing:
                warnings.append(f"[LAYOUT] {msg}")
        else:
            passed.append("[LAYOUT] Grid layouts appear properly configured")

    # Absolute positioning (all sizes)
    if checker.absolute_positions:
        non_decorative = []
        for pos in checker.absolute_positions:
            if 'pointer-events' not in pos:
                non_decorative.append(pos)
        if non_decorative:
            if is_fixed_height:
                errors.append(f"[LAYOUT-FIXED] Found {len(non_decorative)} absolute-positioned element(s) without pointer-events:none in {size_norm}:")
            else:
                warnings.append(f"[LAYOUT] Found {len(non_decorative)} absolute-positioned element(s) without pointer-events:none. Ensure these are decorative only:")
            for p in non_decorative[:3]:
                warnings.append(f"  - {p[:80]}")
        else:
            passed.append("[LAYOUT] Absolute positioning properly configured")
    else:
        passed.append("[LAYOUT] No absolute positioning detected")

    # ===== CONTRAST CHECK =====
    # Check multiple text/background combinations
    contrast_pairs = []

    for css in checker.style_blocks:
        # body color vs background
        body_color = None
        bg_color = None

        m = re.search(r'body\s*\{[^}]*color\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            body_color = m.group(1).strip()
        m = re.search(r'body\s*\{[^}]*background(?:-color)?\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            bg_color = m.group(1).strip()

        # .page background
        m = re.search(r'\.page\s*\{[^}]*background(?:-color)?\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            bg_color = m.group(1).strip()

        if body_color and bg_color:
            contrast_pairs.append(("Body text", body_color, bg_color))

        # .bignum-value color vs background
        bn_color = None
        m = re.search(r'\.bignum-value\s*\{[^}]*color\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            bn_color = m.group(1).strip()
        if bn_color and bg_color:
            contrast_pairs.append(("BigNumber", bn_color, bg_color))

        # Footer text vs footer background
        footer_color = None
        footer_bg = None
        m = re.search(r'\.footer\s*\{[^}]*color\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            footer_color = m.group(1).strip()
        m = re.search(r'\.footer\s*\{[^}]*background(?:-color)?\s*:\s*([^;}]+)', css, re.IGNORECASE | re.DOTALL)
        if m:
            footer_bg = m.group(1).strip()
        if footer_color and footer_bg:
            contrast_pairs.append(("Footer", footer_color, footer_bg))

    contrast_checked = False
    for label, text_c, bg_c in contrast_pairs:
        text_rgb = parse_color(text_c)
        bg_rgb = parse_color(bg_c)
        if text_rgb and bg_rgb:
            ratio = check_contrast(bg_rgb, text_rgb)
            contrast_checked = True
            if ratio >= 4.5:
                passed.append(f"[CONTRAST] {label} contrast ratio: {ratio:.2f}:1 (WCAG AA compliant)")
            elif ratio >= 3.0:
                warnings.append(f"[CONTRAST] {label} contrast ratio: {ratio:.2f}:1 (below WCAG AA 4.5:1, above 3:1)")
            else:
                errors.append(f"[CONTRAST] {label} contrast ratio: {ratio:.2f}:1 (fails WCAG AA 4.5:1)")

    if not contrast_checked:
        warnings.append("[CONTRAST] Could not detect enough color pairs for contrast checking")

    # ===== BORDER RADIUS CONSISTENCY =====
    if checker.border_radii:
        unique_radii = set()
        for r in checker.border_radii:
            nums = re.findall(r'(\d+)px', r)
            unique_radii.update(int(n) for n in nums)

        if len(unique_radii) <= 3:
            passed.append(f"[CONSISTENCY] Border radius values are consistent ({len(unique_radii)} unique values)")
        else:
            warnings.append(f"[CONSISTENCY] Found {len(unique_radii)} different border radius values: {sorted(unique_radii)}px. Consider reducing for visual consistency.")
    else:
        passed.append("[CONSISTENCY] No border radius used (consistent zero-radius approach)")

    # ===== GRADIENT CHECK =====
    gradient_count = len(re.findall(r'linear-gradient|radial-gradient', content, re.IGNORECASE))
    if gradient_count == 0:
        passed.append("[GRADIENT] No gradients used (clean solid-color approach)")
    elif gradient_count <= 3:
        warnings.append(f"[GRADIENT] Found {gradient_count} gradient(s). Ensure each has a clear design purpose.")
    else:
        warnings.append(f"[GRADIENT] Found {gradient_count} gradient(s). Consider reducing to avoid 'AI gradient overload' aesthetic.")

    return errors, warnings, passed


def main():
    parser = argparse.ArgumentParser(description="Quality check for OnePage HTML files")
    parser.add_argument("input", help="Path to HTML file")
    parser.add_argument("--style", help="Design style (B1-B9; B9 relaxes Google blue & color-count checks)", default=None)
    parser.add_argument("--size", help="Canvas size (A1/A2/A3/A4)", default=None)
    parser.add_argument("--no-bignum", action="store_true", help="Skip BigNumber check (user chose E2 — no BigNumber)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"ONEPAGE QUALITY CHECK")
    print(f"File: {args.input}")
    if args.style:
        print(f"Style: {args.style}")
    if args.size:
        print(f"Size: {args.size}")
    print(f"{'='*60}\n")

    errors, warnings, passed = run_checks(args.input, args.style, args.size, args.no_bignum)

    # Print results
    if errors:
        print(f"\n{'='*60}")
        print(f"ERRORS ({len(errors)})")
        print(f"{'='*60}")
        for e in errors:
            print(f"  [X] {e}")

    if warnings:
        print(f"\n{'='*60}")
        print(f"WARNINGS ({len(warnings)})")
        print(f"{'='*60}")
        for w in warnings:
            print(f"  [!] {w}")

    print(f"\n{'='*60}")
    print(f"PASSED ({len(passed)})")
    print(f"{'='*60}")
    for p in passed:
        print(f"  [OK] {p}")

    # Final verdict
    print(f"\n{'='*60}")
    if errors:
        print("VERDICT: FAIL [X]")
        print("Fix all errors before proceeding to screenshot.")
        sys.exit(2)
    elif warnings:
        print("VERDICT: WARN [!]")
        print("Review warnings and fix if possible before screenshot.")
        sys.exit(1)
    else:
        print("VERDICT: PASS [OK]")
        print("All checks passed. Proceed to screenshot.")
        sys.exit(0)


if __name__ == "__main__":
    main()
