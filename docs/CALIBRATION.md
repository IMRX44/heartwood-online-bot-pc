# Calibration guide

The framework is game-agnostic; these steps tie it to *your* Heartwood Online
client. Do them with the game running in a fixed resolution / windowed mode.

## 1. Template images (vision)

The cheapest backend. Capture small reference crops and drop them in
`assets/templates/` with the names referenced in `config/config.yaml`:

| File              | What to crop                                  |
|-------------------|-----------------------------------------------|
| `splash.png`      | the splash/bite animation while fishing       |
| `bobber.png`      | the bobber at rest                            |
| `ore_node.png`    | a mineable ore node                           |
| `tree.png`        | a harvestable tree                            |
| `herb.png`        | a herb node                                   |
| `mob.png`         | a common enemy nameplate / sprite             |
| `recipe_*.png`    | each crafting recipe icon in the craft menu   |

Tips: crop tight, avoid backgrounds that change, keep the game at one zoom
level. Tune `vision.match_threshold` if you get misses/false positives.

## 2. YOLO model (optional, more robust than templates)

1. Capture ~200-500 screenshots of mobs/resources.
2. Label them (e.g. with [Roboflow](https://roboflow.com) or `labelImg`).
3. Train: `yolo detect train data=data.yaml model=yolov8n.pt epochs=100`.
4. Put the resulting `best.pt` path in `vision.yolo_model`.

## 3. Memory offsets (Cheat Engine)

Fill in `src/memory/offsets.py`:

1. Open Cheat Engine, attach to `Heartwood.exe`.
2. Scan your current HP value -> take damage -> rescan -> repeat to narrow down.
3. Right-click the address -> "Find out what accesses this address".
4. Walk the pointer chain back to a **static** base (green address).
5. Record `base_offset` (address - module base) and the deref `chain`.
6. Repeat for max HP, MP, X/Y coords, inventory count.

Then set `backends.memory: true` in the config.

## 4. Packet schema (Wireshark / scapy)

Fill in `src/network/parser.py`:

1. Start Wireshark, filter to the game server IP/port.
2. Perform known actions (move, take damage, loot) and watch which packets fire.
3. Identify the framing (usually `[u16 length][u8 opcode][body]`).
4. Map opcodes in `OPCODES` and decode each `body` layout.
5. Set the real port(s) in `PacketSniffer` and `backends.network: true`.

## Safety

- Keep the panic key (`F12` by default) reachable; it aborts instantly.
- Test on a throwaway account. Botting violates most games' ToS.
