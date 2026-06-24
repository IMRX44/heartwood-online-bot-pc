# Finding the speed address in Heartwood Online

## Tools needed
- [Cheat Engine](https://cheatengine.org) (free)
- Heartwood Online running in windowed mode

---

## Step 1 — Find the speed value

1. Open Cheat Engine → attach to **Heartwood.exe**.
2. In the scan type dropdown pick **Float** (4 bytes).
3. Stand still in-game and scan for your walking speed.  
   For most 2D MMOs this is between **3.0** and **10.0**.
   Start with **Unknown Initial Value** if you don't know it.
4. Walk, then scan **Changed Value**.
5. Stop walking, then scan **Unchanged Value**.
6. Repeat until you have ≤ 20 addresses. The right one will jump to a higher
   number while you're moving.

## Step 2 — Isolate to a static pointer

Green addresses in Cheat Engine are already static; ignore pointer chains.
For non-green addresses:

1. Right-click the address → **"Find out what accesses this address"**.
2. Move your character → see which instruction writes the value.
3. Right-click the instruction → **"Find out what addresses this instruction accesses"** → pointer scan.
4. In the Pointer Scan results sort by offset count and look for a chain with
   ≤ 4 levels that always resolves to the same value across relaunches.

## Step 3 — Record the AOB signature

1. Right-click the final address → **"Browse this memory region"**.
2. Note the 8–16 bytes surrounding the float.  Write them out as hex.
3. Mark bytes that change on reload as wildcards (`?`).

Open `speedhack/src/speed.py` and update:

```python
AOB_PATTERN = bytes([0xXX, 0xXX, 0x00, 0x00, 0x80, 0x3F, 0xXX, 0xXX])
AOB_MASK    = b"xx????xx"    # '?' = wildcard
AOB_OFFSET  = 2              # bytes from match start to the float
BASE_SPEED_HINT = 5.0        # your measured base walking speed
```

## Step 4 — Or use the manual address override

If you just want to test without the AOB scan:

```
python speedhack/cli.py --addr 0x<address> --base 5.0 --mult 2.0
```

or paste the address into the GUI's **Manual Address Override** box.

---

## Why server-side cancels the hack (and why that's fine for a portfolio)

Heartwood Online is **server-authoritative** — the server validates positions
and can reject movement that's too fast. The speed float we patch is the
*client-side* display value, so visually the character zooms, but the server
may rubber-band you back.

For the portfolio, the interesting parts are:

- the Windows memory API usage (`ReadProcessMemory` / `WriteProcessMemory`)
- the AOB scanner (walks `VirtualQueryEx` memory regions)
- the freeze thread with jitter
- the GUI and hotkey system

These are all the same techniques used in production game cheats — the
server-auth limitation is a known game-design defence, not a flaw in your code.
