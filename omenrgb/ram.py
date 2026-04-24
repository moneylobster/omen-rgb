"""Kingston Fury DDR5 direct driver.

Bypasses OpenRGB's detection whitelist by talking directly to the RGB
controllers over SMBus. Protocol reversed from OpenRGB's
KingstonFuryDRAMController.cpp (GPL-2.0, credit to Geofrey Mon and Milan Cermak).
"""

import threading
import time
from contextlib import contextmanager
from typing import Iterable, List, Sequence, Tuple

from smbus2 import SMBus

RGB = Tuple[int, int, int]

_DELAY = 0.01

# Registers (from KingstonFuryDRAMController.h)
_REG_APPLY = 0x08
_REG_MODE = 0x09
_REG_INDEX = 0x0B
_REG_BRIGHTNESS = 0x20
_REG_NUM_SLOTS = 0x27
_REG_BASE_R = 0x50
_REG_BASE_G = 0x51
_REG_BASE_B = 0x52

_BEGIN = 0x53
_END = 0x44
_MODE_DIRECT = 0x10


class FuryRAM:
    """Direct driver for Kingston Fury DDR5 RGB sticks.

    Each stick has 12 LEDs along its top edge. With N sticks you get
    a grid of shape (N, 12) addressable as stick index x LED index.

    Example:
        ram = FuryRAM()
        ram.fill((255, 0, 0))              # all LEDs red
        ram.set_stick(0, [(0,255,0)] * 12) # first stick green
        ram.set_grid([[...] * 12] * 4)     # full matrix
    """

    LEDS_PER_STICK = 12

    def __init__(
        self,
        bus: int = 0,
        addrs: Sequence[int] = (0x60, 0x61, 0x62, 0x63),
        brightness: int = 0xFF,
    ):
        self._bus = SMBus(bus)
        self.addrs = list(addrs)
        self._lock = threading.RLock()
        self._closed = False
        self._init_sticks(brightness)

    # ---- low level ----

    def _w(self, addr: int, reg: int, val: int, retries: int = 5) -> bool:
        for _ in range(retries):
            try:
                self._bus.write_byte_data(addr, reg, val)
                return True
            except OSError:
                time.sleep(_DELAY)
        return False

    @contextmanager
    def _transaction(self):
        """Wrap a batch of writes in begin/end transaction markers."""
        for a in self.addrs:
            self._w(a, _REG_APPLY, _BEGIN)
        time.sleep(_DELAY)
        try:
            yield
        finally:
            for a in self.addrs:
                self._w(a, _REG_APPLY, _END)
            time.sleep(_DELAY)

    def _init_sticks(self, brightness: int) -> None:
        with self._lock, self._transaction():
            for i, a in enumerate(self.addrs):
                self._w(a, _REG_MODE, _MODE_DIRECT)
                self._w(a, _REG_BRIGHTNESS, brightness)
                self._w(a, _REG_INDEX, i)
                self._w(a, _REG_NUM_SLOTS, min(len(self.addrs), 4))

    # ---- public API ----

    @property
    def num_sticks(self) -> int:
        return len(self.addrs)

    @property
    def total_leds(self) -> int:
        return self.num_sticks * self.LEDS_PER_STICK

    @property
    def shape(self) -> Tuple[int, int]:
        """(rows, cols) = (num_sticks, LEDS_PER_STICK)."""
        return (self.num_sticks, self.LEDS_PER_STICK)

    def set_brightness(self, brightness: int) -> None:
        """0..255 brightness for all sticks."""
        with self._lock, self._transaction():
            for a in self.addrs:
                self._w(a, _REG_BRIGHTNESS, brightness & 0xFF)

    def set_grid(self, grid: Sequence[Sequence[RGB]]) -> None:
        """grid[stick_idx][led_idx] -> (r,g,b). Shape must be (num_sticks, 12)."""
        if len(grid) != self.num_sticks:
            raise ValueError(f"grid has {len(grid)} rows, expected {self.num_sticks}")
        for row in grid:
            if len(row) != self.LEDS_PER_STICK:
                raise ValueError(f"row has {len(row)} cols, expected {self.LEDS_PER_STICK}")

        with self._lock, self._transaction():
            for led in range(self.LEDS_PER_STICK):
                for s, a in enumerate(self.addrs):
                    r, g, b = grid[s][led]
                    self._w(a, _REG_BASE_R + 3 * led, r & 0xFF)
                    self._w(a, _REG_BASE_G + 3 * led, g & 0xFF)
                    self._w(a, _REG_BASE_B + 3 * led, b & 0xFF)

    def set_linear(self, pixels: Sequence[RGB]) -> None:
        """Flat list of (r,g,b), length = num_sticks * 12.

        Order: stick 0 LED 0..11, stick 1 LED 0..11, ..."""
        if len(pixels) != self.total_leds:
            raise ValueError(f"got {len(pixels)} pixels, expected {self.total_leds}")
        grid = [
            list(pixels[i * self.LEDS_PER_STICK : (i + 1) * self.LEDS_PER_STICK])
            for i in range(self.num_sticks)
        ]
        self.set_grid(grid)

    def set_stick(self, idx: int, pixels: Sequence[RGB]) -> None:
        """Update a single stick. Other sticks untouched."""
        if len(pixels) != self.LEDS_PER_STICK:
            raise ValueError(f"got {len(pixels)}, expected {self.LEDS_PER_STICK}")
        addr = self.addrs[idx]
        with self._lock, self._transaction():
            for led, (r, g, b) in enumerate(pixels):
                self._w(addr, _REG_BASE_R + 3 * led, r & 0xFF)
                self._w(addr, _REG_BASE_G + 3 * led, g & 0xFF)
                self._w(addr, _REG_BASE_B + 3 * led, b & 0xFF)

    def fill(self, color: RGB) -> None:
        row = [color] * self.LEDS_PER_STICK
        self.set_grid([row] * self.num_sticks)

    def off(self) -> None:
        self.fill((0, 0, 0))

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.off()
        finally:
            self._bus.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
