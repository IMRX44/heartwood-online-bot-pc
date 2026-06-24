"""Passive packet sniffer for game traffic using scapy.

Runs in a background thread, captures TCP payloads to/from the game server,
hands raw bytes to a parser, and publishes decoded events via a callback.
This is read-only observation - no packets are injected.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from src.network.parser import GameEvent, parse_payload
from src.utils.logger import get_logger

log = get_logger("network")

try:
    from scapy.all import TCP, Raw, sniff
    _HAS_SCAPY = True
except Exception:  # pragma: no cover
    _HAS_SCAPY = False


class PacketSniffer:
    def __init__(
        self,
        server_ports: Optional[list[int]] = None,
        on_event: Optional[Callable[[GameEvent], None]] = None,
    ) -> None:
        # TODO: set the real game server port(s) once known.
        self.server_ports = server_ports or [7777]
        self.on_event = on_event
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _handle(self, pkt) -> None:
        if not pkt.haslayer(Raw):
            return
        payload = bytes(pkt[Raw].load)
        event = parse_payload(payload)
        if event and self.on_event:
            self.on_event(event)

    def _run(self) -> None:
        port_filter = " or ".join(f"port {p}" for p in self.server_ports)
        bpf = f"tcp and ({port_filter})"
        log.info("Sniffing with filter: %s", bpf)
        sniff(filter=bpf, prn=self._handle, store=False,
              stop_filter=lambda _: self._stop.is_set())

    def start(self) -> bool:
        if not _HAS_SCAPY:
            log.warning("scapy unavailable - network backend disabled")
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
