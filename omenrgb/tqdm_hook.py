"""tqdm subclass that drives RAM + fans + optional scrolling metrics."""

import atexit
import time
from typing import Any, Dict, Optional

from tqdm import tqdm as _tqdm

from .display import Dashboard, TextDisplay
from .omen import OmenCase
from .ram import FuryRAM, RGB


class RGBtqdm(_tqdm):
    """Drop-in tqdm replacement that mirrors progress on the hardware.

    Usage:
        from omenrgb import RGBtqdm as tqdm
        for x in tqdm(range(100)):
            ...

    The hardware is initialized once on first use and cleaned up at exit.
    Nested bars: only the outermost RGBtqdm drives the hardware (by default).

    Configure globals:
        RGBtqdm.throttle_seconds = 0.15
        RGBtqdm.outer_only = True
    """

    # class-level state (shared across instances)
    _ram: Optional[FuryRAM] = None
    _omen: Optional[OmenCase] = None
    _dash: Optional[Dashboard] = None
    _last_update: float = 0.0
    _depth: int = 0

    throttle_seconds: float = 0.12
    outer_only: bool = True
    progress_color: RGB = (0, 255, 64)

    @classmethod
    def _lazy_init(cls) -> None:
        if cls._dash is not None:
            return
        try:
            cls._ram = FuryRAM()
        except Exception:
            cls._ram = None
        try:
            cls._omen = OmenCase()
        except Exception:
            cls._omen = None
        cls._dash = Dashboard(cls._ram, cls._omen)
        cls._dash.status("running")
        atexit.register(cls._cleanup)

    @classmethod
    def _cleanup(cls) -> None:
        try:
            if cls._dash:
                cls._dash.status("idle")
        except Exception:
            pass

    def __init__(self, *args: Any, **kwargs: Any):
        self._lazy_init()
        self._is_outer = (RGBtqdm._depth == 0)
        RGBtqdm._depth += 1
        super().__init__(*args, **kwargs)

    def update(self, n: int = 1) -> None:
        super().update(n)
        if RGBtqdm.outer_only and not self._is_outer:
            return
        if not self.total:
            return
        now = time.time()
        if now - RGBtqdm._last_update < RGBtqdm.throttle_seconds:
            return
        RGBtqdm._last_update = now
        frac = self.n / self.total
        try:
            RGBtqdm._dash.progress(frac, color=RGBtqdm.progress_color)
        except Exception:
            pass

    def close(self) -> None:
        super().close()
        RGBtqdm._depth = max(0, RGBtqdm._depth - 1)
        if RGBtqdm._depth == 0 and self.total and self.n >= self.total:
            try:
                RGBtqdm._dash.status("done")
            except Exception:
                pass


def get_dashboard() -> Optional[Dashboard]:
    """Access the shared Dashboard (for metric overlays, status changes, etc.)."""
    RGBtqdm._lazy_init()
    return RGBtqdm._dash


def get_text_display() -> Optional[TextDisplay]:
    """Access a TextDisplay bound to the shared RAM instance."""
    RGBtqdm._lazy_init()
    if RGBtqdm._ram is None:
        return None
    return TextDisplay(RGBtqdm._ram)
