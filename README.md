# omenrgb

Python library for controlling HP Omen 40L desktop RGB on Linux, with a
particular focus on ML training status displays.

Talks to hardware directly — no OpenRGB daemon required, no GUI.

## Hardware supported

- **HP Omen 30L / 40L / 45L case RGB** via USB HID (VID `0x103C`, PID `0x84FD`).
  Covers Omen logo, light bar, CPU cooler, front fan ring, and the 3 front fans.
  Per-zone color only — the firmware doesn't expose per-LED.
- **Kingston Fury Beast / Renegade DDR5 RAM** via SMBus. 12 LEDs per stick,
  bypasses OpenRGB's model-code whitelist so sticks with unrecognized IDs
  still work.

## Install

```bash
# system deps
sudo apt install i2c-tools libhidapi-hidraw0
sudo modprobe i2c-dev
echo "i2c-dev" | sudo tee /etc/modules-load.d/i2c-dev.conf

# permissions (log out/in after)
sudo usermod -aG i2c $USER
sudo usermod -aG plugdev $USER
sudo cp 60-omenrgb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# package
pip install .
```

## Quick start

```python
from omenrgb import FuryRAM, OmenCase, Dashboard

ram = FuryRAM()          # all 4 DDR5 sticks
case = OmenCase()        # Omen case
dash = Dashboard(ram, case)

dash.progress(0.42)      # fill 42% of RAM + fans
dash.status("done")      # everything green
```

## ML training integration

```python
from omenrgb import RGBtqdm
for step in RGBtqdm(range(1000)):
    train_step()
```

Status changes from running-blue → progress gradient → done-green automatically.

## Scrolling text on the RAM grid

The 4 sticks × 12 LEDs form a 4×12 character matrix:

```python
from omenrgb import FuryRAM, TextDisplay

ram = FuryRAM()
td = TextDisplay(ram)

td.show("HI", color=(0, 255, 128))                    # static, fits ~3 chars
td.scroll("TRAINING RUN 42", color=(255, 128, 0))     # scroll, any length
td.show_number(98.42, prefix="ACC:", suffix="%", scroll=True)
```

If the physical orientation is upside-down or mirrored, or adjacent LEDs bleed
into each other, tune it at construction:

```python
td = TextDisplay(ram, invert_rows=True, flip_cols=False, spacing=2)
```

- `invert_rows` / `flip_cols` — correct the glyph orientation after running
  `python -m omenrgb.demo orientation`.
- `spacing` — blank columns between characters (default 1). Bump to 2+ if
  adjacent LEDs bleed and letters mush together. Lowering brightness via
  `ram.set_brightness(64)` also helps.

## Big vertically-stacked digits

For training progress where you want a readable two-digit percent, the library
includes a native 4-wide × 6-tall vertical font. Two digits fill the 12-LED
strip exactly, each spanning all 4 sticks:

```python
td = TextDisplay(ram)
td.show_big_number(42, color=(0, 255, 128))                       # both digits green
td.show_big_number(42, color=(0, 255, 128), color2=(255, 128, 0)) # tens green, ones orange
td.show_big_number(7, color=(255, 128, 0))                        # pads to "07"
td.show_vertical("HI", colors=[(255, 0, 0), (0, 0, 255)])         # red H, blue I
```

The font covers digits, A–Z, and common symbols (`. : % - + = /`). Bit 0 of
each row maps to stick 0. `show_vertical` writes the first character at the
high-LED end of the strip by default (reads top-to-bottom on a tall display);
pass `flip_cols=True` to `TextDisplay` if your physical orientation has LED 0
at the top instead.

All text-display methods default to a dim `(10, 10, 10)` background instead
of pure black, which makes adjacent-LED bleed less distracting on unused
pixels. Override `bg=(0, 0, 0)` for true black.

## Live metrics during training

Drop in a scrolling metric update between epochs:

```python
from omenrgb import RGBtqdm, get_text_display

td = get_text_display()

for epoch in RGBtqdm(range(epochs), desc="epoch"):
    loss = train_epoch()
    td.show_number(loss, prefix="L", decimals=2,
                   color=(0, 255, 128) if loss < 1.0 else (255, 160, 0),
                   scroll=True)
```

## Demos

```bash
python -m omenrgb.demo test_pattern   # each stick a different color
python -m omenrgb.demo orientation    # find out which corner is which
python -m omenrgb.demo progress       # progress bar 0→100
python -m omenrgb.demo scroll         # scrolling text
python -m omenrgb.demo vertical       # 4x6 vertical font / big-number demo
python -m omenrgb.demo percent_ramp   # 0→99 big digits with color gradient
python -m omenrgb.demo training       # full simulated training run
python -m omenrgb.demo fans           # 3-stage fan progress
```

## Tuning environment variables

- `OMENRGB_WRITE_DELAY` — seconds to sleep between individual SMBus writes
  (default `0.0005`). Raise to `0.002` if the Fury controllers show corrupted
  colors; the bus can't keep up on some chipsets.
- `OMENRGB_DEBUG=1` — print a line to stderr for every SMBus write that fails
  all retries. Useful when diagnosing color glitches.

## Why not just use OpenRGB?

- OpenRGB's Kingston Fury DDR5 detector has a strict model-code whitelist and
  a signature-check that fails on sticks with flaky reads — your 4th DIMM may
  not show up even though the hardware is fine. We bypass the check entirely.
- OpenRGB requires a running daemon; this is just a library.
- Direct HID is faster than going through the OpenRGB server socket.

## Limitations

- **No per-LED fan control.** The HP Omen firmware doesn't expose it. You get
  one color per fan; use the 3 fans as coarse status bands.
- **Requires i2c + hidraw access.** See the udev rules above.
- **RAM updates are slow-ish.** Each stick gets its own SMBus transaction
  (begin → 36 writes → end) to avoid cross-stick corruption, so a full 48-LED
  frame runs ~150ms on most chipsets. The tqdm hook throttles to 8fps by
  default. Good for progress, not video.
- **Adjacent RAM LEDs bleed.** Individual LEDs are ~3mm apart and the
  diffusers overlap. Use `spacing=2`, `show_big_number` (only 2 wide glyphs),
  or `ram.set_brightness(64)` to keep letters legible.

## Credits

Protocols reversed from OpenRGB (GPL-2.0):
- `KingstonFuryDRAMController.cpp` by Geofrey Mon and Milan Cermak
- `HPOmen30LController.cpp` by the OpenRGB contributors
