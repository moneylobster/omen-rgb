"""omenrgb — drive HP Omen 40L case + Kingston Fury DDR5 RAM from Python.

Quick start:

    from omenrgb import FuryRAM, OmenCase, Dashboard, TextDisplay

    ram = FuryRAM()
    case = OmenCase()
    dash = Dashboard(ram, case)

    dash.progress(0.25)                    # fill ~1/4 of RAM bar
    dash.status("running")                 # color everything status-blue

    td = TextDisplay(ram)
    td.show("LOSS: 0.023", scroll=True)    # scroll text across RAM grid

    # tqdm drop-in
    from omenrgb import RGBtqdm
    for i in RGBtqdm(range(1000)):
        ...
"""

from .display import DEFAULT_VERTICAL_COLORS, Dashboard, ScrollHandle, STATUS, TextDisplay, gradient
from .omen import FAN_ZONES, Mode, OmenCase, Speed, Zone
from .ram import FuryRAM, UnsupportedHostError, _is_supported_host as is_supported_host
from .tqdm_hook import RGBtqdm, get_dashboard, get_text_display

__all__ = [
    "DEFAULT_VERTICAL_COLORS",
    "Dashboard",
    "FAN_ZONES",
    "FuryRAM",
    "UnsupportedHostError",
    "is_supported_host",
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
