"""Bare-bones test — bypasses the library entirely."""
import time
from smbus2 import SMBus

ADDRS = [0x60, 0x61, 0x62, 0x63]

with SMBus(0) as bus:
    def broadcast(reg, val):
        for a in ADDRS:
            bus.write_byte_data(a, reg, val)

    # Init: direct mode, full brightness, index=0 on all
    broadcast(0x08, 0x53)       # begin
    time.sleep(0.01)
    broadcast(0x09, 0x10)       # MODE = DIRECT
    broadcast(0x20, 0xFF)       # BRIGHTNESS = max
    broadcast(0x0B, 0x00)       # INDEX = 0 everywhere
    broadcast(0x27, 4)          # NUM_SLOTS = 4
    broadcast(0x08, 0x44)       # end/apply
    time.sleep(0.01)

    # Paint each stick a distinct color
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    broadcast(0x08, 0x53)       # begin
    for addr, (r, g, b) in zip(ADDRS, colors):
        for led in range(12):
            bus.write_byte_data(addr, 0x50 + 3*led, r)
            bus.write_byte_data(addr, 0x51 + 3*led, g)
            bus.write_byte_data(addr, 0x52 + 3*led, b)
    broadcast(0x08, 0x44)       # end
    time.sleep(5)

    # Off
    broadcast(0x08, 0x53)
    for addr in ADDRS:
        for led in range(12):
            for off in (0x50, 0x51, 0x52):
                bus.write_byte_data(addr, off + 3*led, 0)
    broadcast(0x08, 0x44)


# After the colored-sticks test, try offset-by-offset on stick 0 only
import time
from smbus2 import SMBus

with SMBus(0) as bus:
    def begin(): [bus.write_byte_data(a, 0x08, 0x53) for a in [0x60,0x61,0x62,0x63]]
    def end():   [bus.write_byte_data(a, 0x08, 0x44) for a in [0x60,0x61,0x62,0x63]]

    for offset_name, offset in [("0x50", 0x50), ("0x51", 0x51), ("0x52", 0x52)]:
        print(f"Writing 255 only to offset {offset_name} — what color does stick 0 show?")
        # clear first
        begin()
        for led in range(12):
            for o in (0x50, 0x51, 0x52):
                bus.write_byte_data(0x60, o + 3*led, 0)
        end()
        time.sleep(0.3)
        # light the target offset
        begin()
        for led in range(12):
            bus.write_byte_data(0x60, offset + 3*led, 255)
        end()
        time.sleep(3)
