"""Headless CLI mode for the speed hack (no GUI required).

    python speedhack/cli.py --mult 2.5
    python speedhack/cli.py --addr 0x1A2B3C4D --base 5.0 --mult 3.0
"""
from __future__ import annotations

import argparse
import sys
import time

from speedhack.src.hotkey import HotkeyManager
from speedhack.src.speed import SpeedHack


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Heartwood Speed Hack CLI")
    p.add_argument("--process", default="Heartwood.exe")
    p.add_argument("--mult",    type=float, default=2.0, help="multiplier (default 2.0)")
    p.add_argument("--addr",    help="hex address from Cheat Engine (skips AOB scan)")
    p.add_argument("--base",    type=float, default=5.0, help="base speed when using --addr")
    args = p.parse_args(argv)

    hack = SpeedHack(process_name=args.process, multiplier=args.mult)
    if args.addr:
        hack.set_address(int(args.addr, 16), args.base)
        print(f"[+] Manual address: {args.addr}  base={args.base}")
    else:
        print("[*] Attaching and scanning…")
        if not hack.attach():
            print("[!] Failed to attach — is the game running?", file=sys.stderr)
            return 1
        print(f"[+] Speed address: 0x{hack._addr:X}  base={hack._base_speed:.4f}")

    hk = HotkeyManager()
    active = [False]

    def toggle():
        if active[0]:
            hack.disable()
            active[0] = False
            print("[■] Speed hack DISABLED")
        else:
            hack.multiplier = args.mult
            hack.enable()
            active[0] = True
            print(f"[▶] Speed hack ENABLED  {args.mult}×")

    hk.register(on_toggle=toggle, on_panic=lambda: (hack.disable(), sys.exit(0)))
    print(f"[*] Ready. F1 = toggle ({args.mult}×) | F12 = panic/exit")

    try:
        while True:
            spd = hack.current_speed()
            if spd is not None:
                state = "ON " if hack.is_active else "off"
                print(f"\r  [{state}]  current speed: {spd:8.4f}", end="", flush=True)
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        hack.disable()
        hk.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
