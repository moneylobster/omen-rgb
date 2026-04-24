"""HP Omen 30L/40L case RGB driver via direct HID.

Talks to the Omen controller (VID 0x103C, PID 0x84FD) directly over hidraw,
no OpenRGB daemon needed. Protocol reversed from OpenRGB's
HPOmen30LController.cpp (GPL-2.0).

Hardware limitation: per-zone color only, NOT per-LED. The firmware exposes
7 zones (logo, bar, front fan ring, CPU cooler, bottom/middle/top front fans)
each set to a single color. Built-in animation effects accept up to 6 color
keyframes but the firmware does the animation, not us.
"""

import threading
from enum import IntEnum
from typing import Optional, Tuple

import hid  # python-hid / hidapi binding

RGB = Tuple[int, int, int]

HP_VID = 0x103C
OMEN_PID = 0x84FD

_BUFFER_SIZE = 58  # report ID + 57 data bytes
_VERSION_ID = 0x12
_MAX_BRIGHTNESS = 0x64  # 100


class Zone(IntEnum):
    LOGO = 0x01
    BAR = 0x02
    FRONT_FAN_RING = 0x03  # legacy combined zone; use per-fan zones on 40L/45L
    CPU_COOLER = 0x04
    BOTTOM_FAN = 0x05
    MIDDLE_FAN = 0x06
    TOP_FAN = 0x07


class Mode(IntEnum):
    STATIC = 0x01
    DIRECT = 0x04
    OFF = 0x05
    BREATHING = 0x06
    COLOR_CYCLE = 0x07
    BLINKING = 0x08
    WAVE = 0x09
    RADIAL = 0x0A


class Speed(IntEnum):
    SLOW = 0x01
    MEDIUM = 0x02
    FAST = 0x03


# All fan zones for convenience
FAN_ZONES = (Zone.BOTTOM_FAN, Zone.MIDDLE_FAN, Zone.TOP_FAN)


class OmenCase:
    """Direct HID driver for HP Omen 30L/40L case RGB.

    Example:
        case = OmenCase()
        case.set_zone(Zone.LOGO, (255, 0, 0))
        case.set_fans((0, 255, 0), (0, 255, 0), (0, 255, 0))
        case.off()
    """

    def __init__(self, path: Optional[bytes] = None):
        self._lock = threading.RLock()
        if path is not None:
            self._dev = hid.Device(path=path)
        else:
            try:
                self._dev = hid.Device(vid=HP_VID, pid=OMEN_PID)
            except hid.HIDException as e:
                raise RuntimeError(
                    "Could not open HP Omen HID device. "
                    "Check permissions (udev rules) and that the controller is attached."
                ) from e
        self._closed = False

    # ---- low level ----

    def _write_direct(self, zone: int, color: RGB, brightness: int = _MAX_BRIGHTNESS) -> None:
        """Send a DIRECT-mode color update for one zone."""
        r, g, b = color
        buf = bytearray(_BUFFER_SIZE)

        # Fixed header
        buf[0x02] = _VERSION_ID
        buf[0x03] = Mode.DIRECT
        buf[0x04] = 0x01  # total color count
        buf[0x05] = 0x01  # current color number

        # Color payload: bytes are [brightness, R, G, B] at 0x08 + (zone-1)*4
        index = zone - 1
        buf[0x08 + index * 4] = _MAX_BRIGHTNESS  # per-zone brightness
        buf[0x09 + index * 4] = r & 0xFF
        buf[0x0A + index * 4] = g & 0xFF
        buf[0x0B + index * 4] = b & 0xFF

        buf[0x30] = brightness & 0xFF  # global brightness for this packet
        buf[0x31] = Mode.DIRECT
        buf[0x36] = zone
        buf[0x37] = 0x01  # power state: ON

        self._dev.write(bytes(buf))

    def _write_off(self, zone: int) -> None:
        buf = bytearray(_BUFFER_SIZE)
        buf[0x02] = _VERSION_ID
        buf[0x03] = Mode.OFF
        buf[0x36] = zone
        buf[0x37] = 0x01
        self._dev.write(bytes(buf))

    # ---- public API ----

    def set_zone(self, zone: Zone, color: RGB, brightness: int = 100) -> None:
        """Set one zone to a solid color. brightness: 0..100."""
        with self._lock:
            self._write_direct(int(zone), color, brightness)

    def set_fans(self, bottom: RGB, middle: RGB, top: RGB, brightness: int = 100) -> None:
        """Set all three front fans at once."""
        with self._lock:
            self._write_direct(Zone.BOTTOM_FAN, bottom, brightness)
            self._write_direct(Zone.MIDDLE_FAN, middle, brightness)
            self._write_direct(Zone.TOP_FAN, top, brightness)

    def set_all_fans(self, color: RGB, brightness: int = 100) -> None:
        """All three fans to the same color."""
        self.set_fans(color, color, color, brightness)

    def set_status_accents(
        self,
        logo: Optional[RGB] = None,
        bar: Optional[RGB] = None,
        cpu: Optional[RGB] = None,
    ) -> None:
        """Update accent lights. Pass None to leave unchanged."""
        with self._lock:
            if logo is not None:
                self._write_direct(Zone.LOGO, logo)
            if bar is not None:
                self._write_direct(Zone.BAR, bar)
            if cpu is not None:
                self._write_direct(Zone.CPU_COOLER, cpu)

    def zone_off(self, zone: Zone) -> None:
        with self._lock:
            self._write_off(int(zone))

    def off(self) -> None:
        """Turn off all seven zones."""
        with self._lock:
            for z in Zone:
                self._write_off(int(z))

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.off()
        finally:
            self._dev.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
