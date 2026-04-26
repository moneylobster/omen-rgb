"""Demos for omenrgb. Run individual demos with:

    python -m omenrgb.demo test_pattern
    python -m omenrgb.demo orientation
    python -m omenrgb.demo progress
    python -m omenrgb.demo scroll
    python -m omenrgb.demo training
"""

import math
import random
import sys
import time

from .display import Dashboard, TextDisplay, gradient
from .omen import OmenCase, Zone
from .ram import FuryRAM
from .tqdm_hook import RGBtqdm


def test_pattern():
    """Paint each stick a different color — use to verify physical order."""
    with FuryRAM() as ram:
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (140, 255, 0)]
        for i in range(ram.num_sticks):
            row = [colors[i % len(colors)]] * ram.LEDS_PER_STICK
            ram.set_stick(i, row)
        print(f"stick 0 red, 1 green, 2 blue, 3 yellow — verify which is which")
        time.sleep(6)


def orientation():
    """Show 'R G B Y' spelling out which row is which stick, to fix invert_rows/flip_cols."""
    with FuryRAM() as ram:
        td = TextDisplay(ram)
        # Turn on a single LED on each stick: stick 0 LED 0, stick 1 LED 1, stick 2 LED 2, stick 3 LED 3
        grid = [[(0, 0, 0)] * ram.LEDS_PER_STICK for _ in range(ram.num_sticks)]
        grid[0][0] = (255, 0, 0)      # top-left if invert_rows=False, flip_cols=False
        grid[ram.num_sticks - 1][ram.LEDS_PER_STICK - 1] = (0, 255, 0)
        ram.set_grid(grid)
        print("Red dot should be at ONE corner, green dot at the OPPOSITE corner.")
        print("If red is bottom-left instead of top-left, set invert_rows=True on TextDisplay.")
        print("If red is on the right, set flip_cols=True.")
        time.sleep(6)


def progress():
    """Fill progress bar from 0% to 100%."""
    ram = FuryRAM()
    try:
        case = OmenCase()
    except Exception as e:
        print(f"omen case not available ({e}); RAM only")
        case = None
    dash = Dashboard(ram, case)
    try:
        for i in range(101):
            dash.progress(i / 100)
            time.sleep(0.04)
        time.sleep(1)
        dash.status("done")
        time.sleep(2)
    finally:
        dash.close()


def scroll():
    """Scroll some text across the RAM grid."""
    with FuryRAM() as ram:
        td = TextDisplay(ram)
        print("static 'HI'")
        td.show("HI", color=(0, 255, 128))
        time.sleep(2)
        print("scrolling 'TRAINING'")
        td.show("TRAINING", color=(255, 128, 0), scroll=True, speed=10)
        print("scrolling number")
        td.show(98.42, color=(0, 200, 255), prefix="ACC:", suffix="%", scroll=True)


def vertical():
    """Two big 4x6 digits stacked down the strip — designed for 0..99% readouts."""
    with FuryRAM() as ram:
        ram.set_brightness(64)  # reduce bleed so letters are distinguishable
        td = TextDisplay(ram)
        for pct in (7, 42, 75, 99):
            print(f"big number {pct}")
            td.show(pct, vertical=True, pad=2, colors=[(0, 255, 128), (255, 128, 0)])
            time.sleep(1.5)
        print("letters 'HI' (mixed colors)")
        td.show("HI", vertical=True, colors=[(255, 128, 0), (0, 200, 255)])
        time.sleep(2)


def percent_ramp():
    """Ramp 0..99 as big stacked digits — simulates training progress."""
    with FuryRAM() as ram:
        ram.set_brightness(64)
        td = TextDisplay(ram)
        for pct in range(0, 100, 3):
            tens = gradient((255, 64, 0), (0, 255, 64), pct / 99)
            ones = gradient((0, 200, 255), (255, 200, 0), pct / 99)
            td.show(pct, vertical=True, pad=2, colors=[tens, ones])
            time.sleep(0.08)
        td.show(99, vertical=True, pad=2, colors=[(0, 255, 64), (0, 200, 255)])
        time.sleep(2)


def training():
    """Simulate a training loop with RGBtqdm + live metric overlay."""
    n_epochs = 5
    steps_per_epoch = 80

    td = None
    try:
        from .tqdm_hook import get_text_display
        td = get_text_display()
    except Exception:
        pass

    loss = 2.5
    for epoch in RGBtqdm(range(n_epochs), desc="epoch"):
        for step in RGBtqdm(range(steps_per_epoch), desc=f"ep{epoch}", leave=False):
            time.sleep(0.04)
            loss = max(0.01, loss * 0.997 + random.uniform(-0.02, 0.01))
        # Between epochs, scroll the current loss briefly
        if td is not None:
            td.show(
                loss,
                color=(0, 255, 128) if loss < 1.0 else (255, 160, 0),
                prefix="L",
                decimals=2,
                scroll=True,
                speed=14,
            )


def fans_progress_demo():
    """Show the 3 fans as a 3-stage progress (bottom→middle→top)."""
    with OmenCase() as case:
        dash = Dashboard(omen=case)
        for stage in range(4):
            dash.progress_staged(stage, 3)
            print(f"stage {stage}/3")
            time.sleep(1.5)


DEMOS = {
    "test_pattern": test_pattern,
    "orientation": orientation,
    "progress": progress,
    "scroll": scroll,
    "vertical": vertical,
    "percent_ramp": percent_ramp,
    "training": training,
    "fans": fans_progress_demo,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in DEMOS:
        print("usage: python -m omenrgb.demo <demo>")
        print("demos:", ", ".join(DEMOS))
        sys.exit(1)
    DEMOS[sys.argv[1]]()


if __name__ == "__main__":
    main()
