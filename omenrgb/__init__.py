"""omenrgb — drive HP Omen 40L case + Kingston Fury DDR5 RAM from Python.

Quick start:

    from omenrgb import FuryRAM, OmenCase, Dashboard, TextDisplay

    ram = FuryRAM()
    case = OmenCase()
    dash = Dashboard(ram, case)

    dash.progress(0.25)                    # fill ~1/4 of RAM bar
    dash.status("running")                 # color everything status-blue

    td = TextDisplay(ram)
    td.scroll("LOSS: 0.023")               # scroll text across RAM grid

    # tqdm drop-in
    from omenrgb import RGBtqdm
    for i in RGBtqdm(range(1000)):
        ...
"""

from .display import Dashboard, ScrollHandle, STATUS, TextDisplay, gradient
from .omen import FAN_ZONES, Mode, OmenCase, Speed, Zone
from .ram import FuryRAM
from .tqdm_hook import RGBtqdm, get_dashboard, get_text_display

__all__ = [
    "Dashboard",
    "FAN_ZONES",
    "FuryRAM",
    "Mode",
    "OmenCase",
    "RGBtqdm",
    "STATUS",
    "ScrollHandle",
    "Speed",
    "TextDisplay",
    "Zone",
    "get_dashboard",
    "get_text_display",
    "gradient",
]

__version__ = "0.1.0"
