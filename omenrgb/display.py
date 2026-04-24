"""High-level display API on top of FuryRAM + OmenCase.

- Dashboard: status/progress/gradient helpers across RAM + fans
- TextDisplay: static and scrolling text on the 4x12 RAM grid
- ProgressBar: linear fill over the 48 RAM LEDs
"""

import threading
import time
from typing import List, Optional, Sequence, Tuple

from .font import VERT_CHAR_H, VERT_CHAR_W, glyph_columns, glyph_vertical, render_columns
from .omen import OmenCase, Zone
from .ram import FuryRAM, RGB


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def gradient(cold: RGB, hot: RGB, t: float) -> RGB:
    """Blend two colors. t=0 -> cold, t=1 -> hot."""
    return (
        int(lerp(cold[0], hot[0], t)),
        int(lerp(cold[1], hot[1], t)),
        int(lerp(cold[2], hot[2], t)),
    )


# Status palette
STATUS = {
    "idle": (8, 8, 16),
    "warmup": (255, 160, 0),
    "running": (0, 128, 255),
    "validating": (128, 0, 255),
    "warn": (255, 200, 0),
    "error": (255, 0, 0),
    "done": (0, 255, 64),
}


class Dashboard:
    """Composite display that drives RAM + Omen case together."""

    def __init__(self, ram: Optional[FuryRAM] = None, omen: Optional[OmenCase] = None):
        self.ram = ram
        self.omen = omen

    # ---- progress ----

    def progress(
        self,
        frac: float,
        cold: RGB = (255, 64, 0),
        hot: RGB = (0, 255, 64),
        background: RGB = (8, 8, 8),
    ) -> None:
        """Fill RAM left-to-right with a gradient; fans show overall color."""
        frac = max(0.0, min(1.0, frac))
        if self.ram:
            n = self.ram.total_leds
            lit = int(frac * n)
            pixels: List[RGB] = []
            for i in range(n):
                if i < lit:
                    pixels.append(gradient(cold, hot, i / max(n - 1, 1)))
                else:
                    pixels.append(background)
            self.ram.set_linear(pixels)
        if self.omen:
            color = gradient(cold, hot, frac)
            # Bottom fan fills first (0-33%), middle (33-66%), top (66-100%)
            bottom = color if frac > 0.0 else background
            middle = color if frac > 1 / 3 else background
            top = color if frac > 2 / 3 else background
            self.omen.set_fans(bottom, middle, top)

    def progress_staged(self, stage: int, total_stages: int, color: RGB = (0, 255, 64)) -> None:
        """Discrete stage display — e.g. 3 stages across 3 fans."""
        if self.omen:
            fans = [((0, 0, 0) if i >= stage else color) for i in range(min(total_stages, 3))]
            while len(fans) < 3:
                fans.append((0, 0, 0))
            self.omen.set_fans(*fans[:3])
        if self.ram:
            frac = stage / total_stages if total_stages else 0.0
            n = self.ram.total_leds
            lit = int(frac * n)
            pixels: List[RGB] = [color if i < lit else (0, 0, 0) for i in range(n)]
            self.ram.set_linear(pixels)

    # ---- status ----

    def status(self, kind: str) -> None:
        """One of: idle, warmup, running, validating, warn, error, done."""
        c = STATUS.get(kind, STATUS["idle"])
        if self.ram:
            self.ram.fill(c)
        if self.omen:
            self.omen.set_all_fans(c)
            self.omen.set_status_accents(logo=c, bar=c, cpu=c)

    def accent(self, logo: Optional[RGB] = None, bar: Optional[RGB] = None, cpu: Optional[RGB] = None) -> None:
        if self.omen:
            self.omen.set_status_accents(logo=logo, bar=bar, cpu=cpu)

    # ---- life cycle ----

    def off(self) -> None:
        if self.ram:
            self.ram.off()
        if self.omen:
            self.omen.off()

    def close(self) -> None:
        if self.ram:
            self.ram.close()
        if self.omen:
            self.omen.close()


class TextDisplay:
    """Render static or scrolling text on a 4-row × 12-col RAM grid."""

    WIDTH = 12
    HEIGHT = 4

    def __init__(
        self,
        ram: FuryRAM,
        invert_rows: bool = False,
        flip_cols: bool = False,
        spacing: int = 1,
    ):
        """
        invert_rows: if True, stick index 0 is bottom row instead of top
        flip_cols: if True, LED index 0 is right instead of left
        spacing: blank cols between characters (bump to 2+ if adjacent LEDs bleed)
        Adjust these after running the orientation demo.
        """
        if ram.num_sticks < self.HEIGHT:
            raise ValueError(f"need at least {self.HEIGHT} sticks, got {ram.num_sticks}")
        self.ram = ram
        self.invert_rows = invert_rows
        self.flip_cols = flip_cols
        self.spacing = spacing

    # ---- core rendering ----

    def _columns_to_grid(self, cols: Sequence[int], color: RGB, bg: RGB) -> List[List[RGB]]:
        """Take a list of packed column-bytes, window to WIDTH cols, map to grid."""
        cols = list(cols)[: self.WIDTH]
        while len(cols) < self.WIDTH:
            cols.append(0x0)

        grid = [[bg] * self.ram.LEDS_PER_STICK for _ in range(self.ram.num_sticks)]

        for col_idx in range(self.WIDTH):
            packed = cols[col_idx]
            for row in range(self.HEIGHT):
                lit = (packed >> row) & 1
                if not lit:
                    continue
                stick = (self.HEIGHT - 1 - row) if self.invert_rows else row
                led = (self.ram.LEDS_PER_STICK - 1 - col_idx) if self.flip_cols else col_idx
                grid[stick][led] = color

        return grid

    def show(self, text: str, color: RGB = (0, 255, 0), bg: RGB = (0, 0, 0)) -> None:
        """Display static text (first 12 columns' worth, ~3 chars)."""
        cols = render_columns(text, spacing=self.spacing)
        grid = self._columns_to_grid(cols, color, bg)
        self.ram.set_grid(grid)

    def scroll(
        self,
        text: str,
        color: RGB = (0, 255, 0),
        bg: RGB = (0, 0, 0),
        speed: float = 8.0,
        loops: int = 1,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """Scroll text right-to-left across the grid.

        speed: columns per second
        loops: number of full passes (1 default; use 0 for infinite — use stop_event!)
        stop_event: set to break out early
        """
        padding = [0x0] * self.WIDTH
        base_cols = padding + render_columns(text, spacing=self.spacing) + padding
        step_dt = 1.0 / max(speed, 0.1)
        total_frames = len(base_cols) - self.WIDTH + 1

        loop = 0
        while True:
            for offset in range(total_frames):
                if stop_event is not None and stop_event.is_set():
                    return
                window = base_cols[offset : offset + self.WIDTH]
                grid = self._columns_to_grid(window, color, bg)
                self.ram.set_grid(grid)
                time.sleep(step_dt)
            loop += 1
            if loops and loop >= loops:
                return

    def scroll_async(
        self,
        text: str,
        color: RGB = (0, 255, 0),
        bg: RGB = (0, 0, 0),
        speed: float = 8.0,
    ) -> "ScrollHandle":
        """Start scrolling in a background thread. Returns a handle to stop/join."""
        stop = threading.Event()

        def _run():
            self.scroll(text, color=color, bg=bg, speed=speed, loops=0, stop_event=stop)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return ScrollHandle(thread=t, stop=stop)

    # ---- vertical (rotated 90° CW) rendering ----

    def show_vertical(
        self,
        text: str,
        color: RGB = (0, 255, 0),
        bg: RGB = (0, 0, 0),
        spacing: int = 0,
    ) -> None:
        """Render text using the 4x6 vertical font, stacked down the LED strip.

        Each char is 4 sticks wide × 6 LEDs tall. Two chars fill the 12-LED strip
        exactly with spacing=0 — ideal for a two-digit percent display.
        """
        grid = [[bg] * self.ram.LEDS_PER_STICK for _ in range(self.ram.num_sticks)]

        led_pos = 0
        for ch in text:
            if led_pos >= self.ram.LEDS_PER_STICK:
                break
            rows = glyph_vertical(ch)  # 6 row-bytes, bit c = stick c
            for r in range(VERT_CHAR_H):
                led = led_pos + r
                if led >= self.ram.LEDS_PER_STICK:
                    break
                row_byte = rows[r]
                for c in range(VERT_CHAR_W):
                    if c >= self.ram.num_sticks:
                        break
                    if not (row_byte >> c) & 1:
                        continue
                    stick = (self.ram.num_sticks - 1 - c) if self.invert_rows else c
                    led_idx = (self.ram.LEDS_PER_STICK - 1 - led) if self.flip_cols else led
                    grid[stick][led_idx] = color
            led_pos += VERT_CHAR_H + spacing

        self.ram.set_grid(grid)

    def show_big_number(
        self,
        value: float,
        color: RGB = (0, 255, 0),
        bg: RGB = (0, 0, 0),
    ) -> None:
        """Display a 0..99 integer as two big vertically-stacked digits.

        Clamps to two digits: values < 10 get a leading zero, >99 get clamped to 99.
        """
        n = max(0, min(99, int(value)))
        self.show_vertical(f"{n:02d}", color=color, bg=bg, spacing=0)

    # ---- number helpers ----

    def show_number(
        self,
        value: float,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 2,
        color: RGB = (0, 255, 0),
        bg: RGB = (0, 0, 0),
        scroll: bool = False,
        speed: float = 8.0,
    ) -> None:
        """Format and show a number. Auto-scrolls if too long to fit."""
        fmt_value = f"{value:.{decimals}f}" if isinstance(value, float) else str(value)
        text = f"{prefix}{fmt_value}{suffix}"
        # 3 cols per char + 1 spacing + trailing padding; fits roughly 3 chars static
        fits_static = (len(text) * 4 - 1) <= self.WIDTH
        if scroll or not fits_static:
            self.scroll(text, color=color, bg=bg, speed=speed, loops=1)
        else:
            self.show(text, color=color, bg=bg)


class ScrollHandle:
    """Handle for an async scroll. Call stop() to cancel."""

    def __init__(self, thread: threading.Thread, stop: threading.Event):
        self._thread = thread
        self._stop = stop

    def stop(self, join: bool = True, timeout: float = 2.0) -> None:
        self._stop.set()
        if join:
            self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()
