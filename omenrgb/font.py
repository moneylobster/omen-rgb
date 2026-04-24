"""A 4-row bitmap font for the Fury RAM grid.

The RAM grid is 4 rows × 12 cols. Characters are 3 cols wide × 4 rows tall
so we can fit 3 chars (with 1-col spacing they'd be 4 cells = 3 chars)
or show a scrolling ticker across longer text.

Each glyph is represented column-major as a tuple of 3 integers. Each int
is a 4-bit row pattern where bit 0 = top row, bit 3 = bottom row. This makes
the scroller trivial: flatten glyph columns into a single list and window over it.

Example — '0':
    X X X     col 0: rows 0,1,2,3 -> bits 1111 = 0xF
    X . X     col 1: rows 0,3     -> bits 1001 = 0x9
    X . X     col 2: rows 0,1,2,3 -> bits 1111 = 0xF
    X X X
"""

from typing import Dict, List, Tuple

# Column-major: each character is (col0, col1, col2) with rows packed in bits
# Bit 0 = row 0 (top), bit 3 = row 3 (bottom)
FONT_3x4: Dict[str, Tuple[int, ...]] = {
    ' ': (0x0, 0x0, 0x0),
    '0': (0xF, 0x9, 0xF),
    '1': (0x2, 0xF, 0x0),
    '2': (0x9, 0xD, 0xB),
    '3': (0x9, 0xD, 0xF),
    '4': (0x7, 0x4, 0xF),
    '5': (0xF, 0xD, 0xD),
    '6': (0xE, 0xD, 0xD),
    '7': (0x1, 0x1, 0xF),
    '8': (0xF, 0xB, 0xF),
    '9': (0x7, 0x5, 0xF),
    '.': (0x0, 0x8, 0x0),
    ':': (0x0, 0xA, 0x0),
    '%': (0xD, 0x4, 0xB),
    '-': (0x4, 0x4, 0x4),
    '+': (0x4, 0xE, 0x4),
    '/': (0x8, 0x6, 0x1),
    '=': (0xA, 0xA, 0xA),
    'A': (0xE, 0x5, 0xE),
    'B': (0xF, 0xB, 0xE),
    'C': (0xF, 0x9, 0x9),
    'D': (0xF, 0x9, 0x6),
    'E': (0xF, 0xB, 0x9),
    'F': (0xF, 0x3, 0x1),
    'G': (0xF, 0x9, 0xD),
    'H': (0xF, 0x4, 0xF),
    'I': (0x9, 0xF, 0x9),
    'J': (0x8, 0x8, 0xF),
    'K': (0xF, 0x4, 0xB),
    'L': (0xF, 0x8, 0x8),
    'M': (0xF, 0x2, 0xF),
    'N': (0xF, 0x1, 0xF),
    'O': (0xF, 0x9, 0xF),
    'P': (0xF, 0x3, 0x3),
    'Q': (0xF, 0x9, 0xF),  # Q≈O at 3x4
    'R': (0xF, 0x3, 0xE),
    'S': (0xB, 0xB, 0xD),
    'T': (0x1, 0xF, 0x1),
    'U': (0xF, 0x8, 0xF),
    'V': (0x7, 0x8, 0x7),
    'W': (0xF, 0x4, 0xF),  # W≈M
    'X': (0x9, 0x6, 0x9),
    'Y': (0x3, 0xC, 0x3),
    'Z': (0xD, 0xB, 0xB),  # Z≈2
}


def glyph_columns(char: str) -> Tuple[int, ...]:
    """Get the 3 column-bytes for a character. Falls back to space."""
    return FONT_3x4.get(char.upper(), FONT_3x4[' '])


def render_columns(text: str, spacing: int = 1) -> List[int]:
    """Render a string to a flat list of column-bytes (4 bits each, one per row).

    Returns: list of length ~ 4 * len(text) columns (3 per char + spacing).
    """
    cols: List[int] = []
    for i, ch in enumerate(text):
        cols.extend(glyph_columns(ch))
        if i < len(text) - 1:
            cols.extend([0x0] * spacing)
    return cols


def column_to_rows(col_byte: int, height: int = 4) -> List[int]:
    """Expand a packed column byte into a list of 0/1 per row (top-to-bottom)."""
    return [(col_byte >> row) & 1 for row in range(height)]


def render_bitmap(text: str, spacing: int = 1) -> List[List[int]]:
    """Render text to a 2D bitmap [rows][cols] of 0/1.

    Useful for static display or external rendering.
    """
    cols = render_columns(text, spacing)
    return [[(c >> row) & 1 for c in cols] for row in range(4)]
