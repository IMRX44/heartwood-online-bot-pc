"""Process attachment and raw memory I/O (Windows only, ctypes — no deps).

Provides:
  ProcessHandle  — attach by PID or by .exe name
  read_float / write_float helpers
  aob_scan        — pattern search across all readable memory regions
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import struct
from typing import Generator, Iterable, Optional, Sequence

# ------------------------------------------------------------------
# Windows API surface
# ------------------------------------------------------------------
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT         = 0x1000
TH32CS_SNAPPROCESS = 0x2
PAGE_READABLE      = 0x02 | 0x04 | 0x20 | 0x40   # R / RW / ER / ERW

try:
    _k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    _HAS_WIN = True
except AttributeError:
    _HAS_WIN = False


# ------------------------------------------------------------------
# MEMORY_BASIC_INFORMATION (pointer-width aware)
# ------------------------------------------------------------------
def _mbi_type():
    import platform
    _P = ctypes.c_uint64 if platform.architecture()[0] == "64bit" else ctypes.c_uint32

    class MBI(ctypes.Structure):
        _fields_ = [
            ("BaseAddress",       _P),
            ("AllocationBase",    _P),
            ("AllocationProtect", ctypes.wintypes.DWORD),
            ("__pad",             ctypes.wintypes.WORD),
            ("RegionSize",        _P),
            ("State",             ctypes.wintypes.DWORD),
            ("Protect",           ctypes.wintypes.DWORD),
            ("Type",              ctypes.wintypes.DWORD),
        ]
    return MBI

_MBI = _mbi_type() if _HAS_WIN else None


# ------------------------------------------------------------------
# PROCESSENTRY32 for enumeration
# ------------------------------------------------------------------
class _PE32(ctypes.Structure):
    _fields_ = [
        ("dwSize",              ctypes.wintypes.DWORD),
        ("cntUsage",            ctypes.wintypes.DWORD),
        ("th32ProcessID",       ctypes.wintypes.DWORD),
        ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID",        ctypes.wintypes.DWORD),
        ("cntThreads",          ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase",      ctypes.c_long),
        ("dwFlags",             ctypes.wintypes.DWORD),
        ("szExeFile",           ctypes.c_char * 260),
    ]


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
class ProcessHandle:
    """Open PROCESS_ALL_ACCESS handle to a target process."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self._h = None
        if not _HAS_WIN:
            return
        h = _k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h:
            raise OSError(f"OpenProcess failed (PID={pid}, err={_k32.GetLastError()})")
        self._h = h

    def close(self) -> None:
        if self._h and _HAS_WIN:
            _k32.CloseHandle(self._h)
            self._h = None

    def __enter__(self) -> "ProcessHandle":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ---- read --------------------------------------------------------
    def read_bytes(self, addr: int, n: int) -> Optional[bytes]:
        if not self._h:
            return None
        buf  = ctypes.create_string_buffer(n)
        read = ctypes.c_size_t(0)
        ok   = _k32.ReadProcessMemory(self._h, ctypes.c_void_p(addr),
                                      buf, n, ctypes.byref(read))
        return bytes(buf) if ok and read.value == n else None

    def read_float(self, addr: int) -> Optional[float]:
        b = self.read_bytes(addr, 4)
        return struct.unpack_from("<f", b)[0] if b else None

    def read_i32(self, addr: int) -> Optional[int]:
        b = self.read_bytes(addr, 4)
        return struct.unpack_from("<i", b)[0] if b else None

    # ---- write -------------------------------------------------------
    def write_bytes(self, addr: int, data: bytes) -> bool:
        if not self._h:
            return False
        buf     = ctypes.create_string_buffer(data)
        written = ctypes.c_size_t(0)
        ok      = _k32.WriteProcessMemory(self._h, ctypes.c_void_p(addr),
                                          buf, len(data), ctypes.byref(written))
        return bool(ok) and written.value == len(data)

    def write_float(self, addr: int, value: float) -> bool:
        return self.write_bytes(addr, struct.pack("<f", value))

    # ---- AOB scan ----------------------------------------------------
    def aob_scan(
        self,
        pattern: bytes,
        mask:    bytes,
        start:   int = 0,
        end:     int = 0x7FFFFFFF,
        chunk:   int = 0x40000,   # 256 KB
    ) -> Generator[int, None, None]:
        """Yield every address where pattern matches under mask.

        mask:  b'x' = must match byte, b'?' = wildcard
        """
        if not (_HAS_WIN and self._h):
            return
        plen = len(pattern)
        addr = start
        mbi  = _MBI()

        while addr < end:
            if not _k32.VirtualQueryEx(self._h, ctypes.c_void_p(addr),
                                       ctypes.byref(mbi), ctypes.sizeof(mbi)):
                addr += 0x1000
                continue

            r_end = mbi.BaseAddress + mbi.RegionSize
            if mbi.State == MEM_COMMIT and (mbi.Protect & PAGE_READABLE):
                cur = addr
                while cur < min(r_end, end):
                    n    = min(chunk, int(min(r_end, end)) - cur)
                    data = self.read_bytes(cur, n)
                    if data:
                        for i in range(len(data) - plen + 1):
                            if _aob_match(data, i, pattern, mask):
                                yield cur + i
                    cur += n - plen   # overlap so we don't miss cross-chunk hits
            addr = max(int(r_end), addr + 0x1000)


def _aob_match(data: bytes, offset: int, pat: bytes, mask: bytes) -> bool:
    for j in range(len(pat)):
        if mask[j] == ord(b"x") and data[offset + j] != pat[j]:
            return False
    return True


def find_pid(exe_name: str) -> Optional[int]:
    """Return the PID of the first running process whose name matches exe_name."""
    if not _HAS_WIN:
        return None
    snap  = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = _PE32()
    entry.dwSize = ctypes.sizeof(_PE32)
    found = None
    if _k32.Process32First(snap, ctypes.byref(entry)):
        while True:
            if entry.szExeFile.decode(errors="replace").lower() == exe_name.lower():
                found = entry.th32ProcessID
                break
            if not _k32.Process32Next(snap, ctypes.byref(entry)):
                break
    _k32.CloseHandle(snap)
    return found


def open_by_name(exe_name: str) -> Optional[ProcessHandle]:
    """Attach to a running process by .exe name; return None on failure."""
    pid = find_pid(exe_name)
    if pid is None:
        return None
    try:
        return ProcessHandle(pid)
    except OSError:
        return None
