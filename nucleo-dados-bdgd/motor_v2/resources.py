"""Resource control for local runs: a pre-flight RAM guard and a background peak-RSS sampler (no agent polling)."""
import threading
import time
import psutil


def guard(min_available_gb=3.0):
    """Refuse to start when available RAM is below the floor (instead of letting the machine swap or OOM)."""
    free = psutil.virtual_memory().available / 2**30
    if free < min_available_gb:
        raise MemoryError(f'available RAM {free:.1f} GiB below the {min_available_gb} GiB floor; close applications and retry')
    return free


class Sampler:
    """Samples this process (and children) every `period` seconds; `report()` gives peak RSS and wall time."""

    def __init__(self, period=0.5):
        self.period, self.peak, self._stop = period, 0, threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _rss(self):
        p = psutil.Process()
        total = p.memory_info().rss
        for c in p.children(recursive=True):
            try:
                total += c.memory_info().rss
            except psutil.Error:
                pass
        return total

    def _loop(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, self._rss())
            time.sleep(self.period)

    def __enter__(self):
        self.start = time.monotonic()
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join()
        self.peak = max(self.peak, self._rss())

    def report(self):
        return dict(peak_rss_gib=round(self.peak / 2**30, 3), wall_seconds=round(time.monotonic() - self.start, 1))
