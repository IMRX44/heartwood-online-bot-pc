"""Low-level memory primitives: AOB scan, read/write helpers.

Wraps Windows ReadProcessMemory / WriteProcessMemory via ctypes so every
higher-level cheat module gets a single, testable abstraction.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import struct
from typing import Generator, Optional

from src.utils.logger import get_logger

log = get_logger("cheat.mem")

# Windows constants
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
PAGE_READABLE = 0x02 | 0x04 | 0x20 | 0x40  # READONLY | READWRITE | EXECUTE_READ | EXECUTE_READWRITE

try:
    _k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    _HAS_WIN32 = True
except AttributeError:
    _HAS_WIN32 = False
    log.warning("Not running on Windows - memory operations disabled")


class MemoryHandle:
    """An open handle to a target process."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self._handle = None
        if _HAS_WIN32:
            self._handle = _k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not self._handle:
                raise OSError(f"OpenProcess failed for PID {pid} (error {_k32.GetLastError()})")

    def close(self) -> None:
        if self._handle and _HAS_WIN32:
            _k32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self) -> "MemoryHandle":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # --- read -----------------------------------------------------------
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._handle:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = _k32.ReadProcessMemory(self._handle, ctypes.c_void_p(address),
                                    buf, size, ctypes.byref(read))
        return bytes(buf) if ok and read.value == size else None

    def read_float(self, address: int) -> Optional[float]:
        data = self.read_bytes(address, 4)
        return struct.unpack_from("<f", data)[0] if data else None

    def read_int32(self, address: int) -> Optional[int]:
        data = self.read_bytes(address, 4)
        return struct.unpack_from("<i", data)[0] if data else None

    def read_uint32(self, address: int) -> Optional[int]:
        data = self.read_bytes(address, 4)
        return struct.unpack_from("<I", data)[0] if data else None

    # --- write ----------------------------------------------------------
    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._handle:
            return False
        buf = ctypes.create_string_buffer(data)
        written = ctypes.c_size_t(0)
        ok = bool(_k32.WriteProcessMemory(self._handle, ctypes.c_void_p(address),
                                          buf, len(data), ctypes.byref(written)))
        return ok and written.value == len(data)

    def write_float(self, address: int, value: float) -> bool:
        return self.write_bytes(address, struct.pack("<f", value))

    def write_int32(self, address: int, value: int) -> bool:
        return self.write_bytes(address, struct.pack("<i", value))

    # --- AOB (Array-of-Bytes) scan -------------------------------------
    def aob_scan(
        self,
        pattern: bytes,
        mask: bytes,
        start: int = 0x0,
        end: int = 0x7FFFFFFF,
    ) -> Generator[int, None, None]:
        """Yield every address in [start, end) where `pattern` matches under `mask`.

        `mask` is a byte string where b'x' means match and b'?' means wildcard.
        Example:
            pattern = bytes([0x89, 0x00, 0x00, 0x00, 0x3F])
            mask    = b"x???x"   # only first and last bytes must match
        """
        if not _HAS_WIN32 or not self._handle:
            return

        chunk = 0x1000 * 64  # 256 KB per read
        addr = start
        plen = len(pattern)

        MEMORY_BASIC_INFORMATION = _make_mbi()

        while addr < end:
            mbi = MEMORY_BASIC_INFORMATION()
            size = ctypes.sizeof(mbi)
            if not _k32.VirtualQueryEx(self._handle, ctypes.c_void_p(addr),
                                       ctypes.byref(mbi), size):
                addr += 0x1000
                continue

            region_end = mbi.BaseAddress + mbi.RegionSize
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                scan_end = min(region_end, end)
                cur = addr
                while cur < scan_end:
                    read_size = min(chunk, scan_end - cur)
                    data = self.read_bytes(cur, read_size)
                    if data:
                        for i in range(len(data) - plen + 1):
                            if _match(data, i, pattern, mask):
                                yield cur + i
                    cur += read_size - plen  # overlap to catch cross-chunk hits

            addr = max(region_end, addr + 0x1000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match(data: bytes, offset: int, pattern: bytes, mask: bytes) -> bool:
    for j, (p, m) in enumerate(zip(pattern, mask)):
        if m == ord(b"x") and data[offset + j] != p:
            return False
    return True


def _make_mbi():
    """Return a MEMORY_BASIC_INFORMATION ctypes struct (pointer-size aware)."""
    import platform
    is64 = platform.architecture()[0] == "64bit"
    ptr = ctypes.c_uint64 if is64 else ctypes.c_uint32

    class MBI(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ptr),
            ("AllocationBase", ptr),
            ("AllocationProtect", ctypes.wintypes.DWORD),
            ("_pad", ctypes.wintypes.WORD) if is64 else ("", ctypes.c_char * 0),
            ("RegionSize", ptr),
            ("State", ctypes.wintypes.DWORD),
            ("Protect", ctypes.wintypes.DWORD),
            ("Type", ctypes.wintypes.DWORD),
        ]

    return MBI


def open_process_by_name(name: str) -> Optional["MemoryHandle"]:
    """Find a running process by .exe name and return an open handle, or None."""
    if not _HAS_WIN32:
        return None
    import ctypes.wintypes

    TH32CS_SNAPPROCESS = 0x2

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("cntUsage", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("cntThreads", ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    if not _k32.Process32First(snap, ctypes.byref(entry)):
        _k32.CloseHandle(snap)
        return None
    while True:
        if entry.szExeFile.decode(errors="replace").lower() == name.lower():
            pid = entry.th32ProcessID
            _k32.CloseHandle(snap)
            try:
                return MemoryHandle(pid)
            except OSError as exc:
                log.error("Failed to open process %s (PID %d): %s", name, pid, exc)
                return None
        if not _k32.Process32Next(snap, ctypes.byref(entry)):
            break
    _k32.CloseHandle(snap)
    return None
