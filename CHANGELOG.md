# Changelog

All notable changes to the Onepager skill are documented in this file.

## [1.4.0] - 2026-05-29

### Added
- **B9 Google Native style**: Complete design specification with Light (Classic Four-Color) and Dark (I/O) dual palette, card styles, heading styles, color budget mapping, icon style, BigNumber CSS, and signature styling
- **B9 typography mapping**: Inter + Noto Sans SC font stack, Chinese-specific weight rules, letter-spacing guidelines, Google Fonts loading
- **B9 diagram color palette**: Brand four-color data series for both Light and Dark modes
- **B9 visual standards**: Icon style and BigNumber differentiation table entries
- **A4 size typography table**: Complete font size ladder for 1080×1440px poster size
- **A4 BigNumber size specs**: Minimum, recommended, unit, and label sizes
- **A4 visual flow direction**: Z-pattern recommendation in visual-standards.md
- **Quote block and Key Insight block**: E2 (no BigNumber) alternative HTML templates in base-skeleton.html
- **12 additional SVG icons**: search, link, mail, calendar, clock, star, download, home, shield, lightbulb, play, code
- **Page size adaptation classes**: `.page-a1` / `.page-a2` / `.page-a3` / `.page-a4` CSS classes in template
- **B9 color block utility classes**: `.color-block-blue` / `.color-block-red` / `.color-block-yellow` / `.color-block-green` in template
- **CHANGELOG.md**: This file

### Changed
- **SKILL.md phase numbering**: Renumbered from 1/2/3/4/4.5/5 to 1/2/3/4/5/6 for clarity
- **Quality check deduplication**: Removed duplicate `quality_check.py` execution; now only runs once in Phase 5 (was Phase 4.5 + Phase 5.2)
- **File naming format**: Date format explicitly specified as `YYYYMMDD`; iteration version appended after date (`{topic}-{size}-{style}-{YYYYMMDD}[-vN].html`)
- **quality_check.py major improvements**:
  - `--size` parameter now actually used: A2/A3/A4 trigger stricter fixed-height layout checks (flex:1 becomes ERROR, missing grid-template-rows becomes WARNING)
  - Color deduplication: colors normalized to RGB tuples before counting, eliminating false duplicates from different color syntaxes
  - Emoji detection: uses `unicodedata.category()` for broader coverage (Emoji Keycap, skin tone modifiers, Supplemental Symbols Extended-A, etc.)
  - Removed redundant flex:1 detection code
  - Multi-element contrast checking: now checks Body text, BigNumber, and Footer independently
  - Removed emoji from terminal output (uses `[X]`/`[!]`/`[OK]` instead of emoji)
  - Removed `#2563eb` from `known_ai_colors` to avoid false positives with B5 (宝蓝)
- **capture.py improvements**:
  - Explicit timeout parameter (`--timeout`, default 30000ms)
  - Graceful timeout handling with warning instead of crash
  - Uses `document.fonts.ready` for font loading detection instead of fixed 2000ms wait
  - Reduced post-render buffer from 2000ms to 500ms
  - Added brief re-render wait after viewport resize for fixed-size screenshots
- **base-skeleton.html**: Removed default decorative `.page::before` blob (was contradicting anti-AI-taste rules)
- **layout-specs.md**: Title updated from "三种尺寸" to "四种尺寸"
- **design-styles.md**: Title updated from "八种" to "九种"; color budget exception text updated to include B9
- **guideline.md**: Repositioned as "design theory reference" rather than operational guide; removed outdated 4-step prompt template
- **README.md**: Fixed size counts (3→4 sizes); fixed layout-specs.md description in file structure
- **visual-standards.md**: Added A4 visual flow direction; updated icon style and BigNumber tables with B9 rows

### Fixed
- `quality_check.py`: Blue-purple detection no longer flags `#2563eb` alone (was in `known_ai_colors` with comment "only flag when paired with purple" but flagged unconditionally)
- `quality_check.py`: `flex:1` inline style check had redundant condition (`s` was already `style.replace(" ", "")`)
