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

If the physical orientation is upside-down or mirrored, fix it at construction:

```python
td = TextDisplay(ram, invert_rows=True, flip_cols=False)
```

Run `python -m omenrgb.demo orientation` to see which corners are which.

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
python -m omenrgb.demo training       # full simulated training run
python -m omenrgb.demo fans           # 3-stage fan progress
```

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
- **RAM updates are slow-ish.** ~48 SMBus writes per frame = ~100ms on most
  chipsets. The tqdm hook throttles to 8fps by default. Good for progress,
  not video.

## Credits

Protocols reversed from OpenRGB (GPL-2.0):
- `KingstonFuryDRAMController.cpp` by Geofrey Mon and Milan Cermak
- `HPOmen30LController.cpp` by the OpenRGB contributors
