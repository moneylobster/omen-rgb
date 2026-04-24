import time
from smbus2 import SMBus

ADDRS = [0x60, 0x61, 0x62, 0x63]
WRITE_DELAY = 0.0005   # 500us between writes
RETRY_DELAY = 0.005

def safe_write(bus, addr, reg, val, retries=5):
    for attempt in range(retries):
        try:
            bus.write_byte_data(addr, reg, val)
            time.sleep(WRITE_DELAY)
            return True
        except OSError as e:
            time.sleep(RETRY_DELAY * (attempt + 1))
    print(f"  FAIL addr=0x{addr:02x} reg=0x{reg:02x} val={val}")
    return False

def begin(bus):
    for a in ADDRS: safe_write(bus, a, 0x08, 0x53)
    time.sleep(0.01)

def end(bus):
    for a in ADDRS: safe_write(bus, a, 0x08, 0x44)
    time.sleep(0.01)

with SMBus(0) as bus:
    # init
    begin(bus)
    for a in ADDRS:
        safe_write(bus, a, 0x09, 0x10)   # direct mode
        safe_write(bus, a, 0x20, 0xFF)   # brightness
        safe_write(bus, a, 0x0B, 0x00)   # index=0
        safe_write(bus, a, 0x27, 4)      # num slots
    end(bus)

    # test each offset on stick 0
    for offset_name, offset in [("0x50 (R?)", 0x50), ("0x51 (?)", 0x51), ("0x52 (?)", 0x52)]:
        print(f"--- writing 255 to offset {offset_name} on stick 0 ---")
        # clear
        begin(bus)
        for led in range(12):
            for o in (0x50, 0x51, 0x52):
                safe_write(bus, 0x60, o + 3*led, 0)
        end(bus)
        time.sleep(0.5)
        # light target
        begin(bus)
        failures = 0
        for led in range(12):
            if not safe_write(bus, 0x60, offset + 3*led, 255):
                failures += 1
        end(bus)
        print(f"  {failures}/12 writes failed")
        time.sleep(3)

    # off
    begin(bus)
    for a in ADDRS:
        for led in range(12):
            for o in (0x50, 0x51, 0x52):
                safe_write(bus, a, o + 3*led, 0)
    end(bus)
