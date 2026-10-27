"""Fetch individual entries of a large remote zip using HTTP Range requests (instead of downloading all of it)."""
import http.client
import io
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


class RangeFile(io.RawIOBase):
    """Read-only seekable file over HTTP Range requests with a small read-ahead cache."""

    def __init__(self, url: str, read_ahead: int = 1 << 20, timeout: float = 120.0, retries: int = 6,
                 backoff: float = 2.0):
        self.url, self.read_ahead, self.timeout = url, read_ahead, timeout
        self.retries, self.backoff = retries, backoff
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=timeout) as r:
            self.size = int(r.headers["Content-Length"])
        self.pos, self._buf, self._start = 0, b"", 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def _fetch(self, start: int, n: int) -> bytes:
        end = min(self.size - 1, start + n - 1)
        want = end - start + 1
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = r.read()
            except (http.client.HTTPException, urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == self.retries:
                    raise IOError(f"range request failed after {attempt + 1} attempts: {e!r}") from e
                time.sleep(self.backoff * (attempt + 1))  # transient network trouble: wait and retry this chunk
                continue
            if len(data) != want:
                raise IOError(f"server ignored the Range header (got {len(data)} bytes, wanted {want})")
            return data
        raise AssertionError("unreachable")

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        if not (self._start <= self.pos and self.pos + n <= self._start + len(self._buf)):
            self._buf, self._start = self._fetch(self.pos, max(n, self.read_ahead)), self.pos
        out = self._buf[self.pos - self._start: self.pos - self._start + n]
        self.pos += len(out)
        return out

    def readinto(self, b) -> int:  # type: ignore[override]
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def list_entries(url: str) -> dict[str, int]:
    """name -> uncompressed size for every file in the remote zip."""
    z = zipfile.ZipFile(RangeFile(url))
    return {i.filename: i.file_size for i in z.infolist() if not i.is_dir()}


def fetch_entry(url: str, name: str, dest: Path, chunk: int = 1 << 20) -> int:
    """Stream one entry to dest (via a .part file); returns bytes written. Skips if already complete."""
    z = zipfile.ZipFile(RangeFile(url))
    info = z.getinfo(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == info.file_size:
        return 0
    part = dest.with_suffix(dest.suffix + ".part")
    written = 0
    with z.open(info) as src, part.open("wb") as out:
        while data := src.read(chunk):
            out.write(data)
            written += len(data)
    if written != info.file_size:
        raise IOError(f"{name}: wrote {written} bytes, expected {info.file_size}")
    part.replace(dest)
    return written
