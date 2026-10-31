"""
Read live EEG samples from PiEEG Server over WebSocket.

PiEEG Server runs on the Raspberry Pi and streams one JSON message per sample:

    {"t": 1711234567.123, "n": 42, "channels": [12.34, -5.67, ...]}

    t         Unix time in seconds
    n         sample number, counts up by 1
    channels  microvolts, one value per channel (8 for PiEEG-8)

Other messages (the welcome message, status updates) are skipped.

Usage:
    from eeg_stream import stream_samples
    for t, n, uv in stream_samples("raspberrypi.local"):
        print(n, uv[0])
"""

import asyncio
import json
import queue
import threading
from dataclasses import dataclass

import websockets

DEFAULT_HOST = "raspberrypi.local"
DEFAULT_PORT = 1616
SAMPLE_RATE = 250  # Hz, PiEEG default


@dataclass
class Sample:
    t: float
    n: int
    uv: list


def parse_message(raw: str):
    """Return a Sample for a data frame, None for anything else."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(msg, dict):
        return None
    ch = msg.get("channels")
    if "n" not in msg or not isinstance(ch, list):
        return None  # welcome message has "channels": 8 (an int)
    return Sample(t=float(msg.get("t", 0.0)), n=int(msg["n"]), uv=[float(v) for v in ch])


async def _reader(url: str, out: "queue.Queue", stop: threading.Event):
    async with websockets.connect(url, max_queue=4096) as ws:
        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            s = parse_message(raw)
            if s is not None:
                out.put(s)


class EEGStream:
    """Background reader. Call .get_new() to drain samples received so far."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.url = f"ws://{host}:{port}"
        self._q: "queue.Queue[Sample]" = queue.Queue()
        self._stop = threading.Event()
        self.error = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        try:
            asyncio.run(_reader(self.url, self._q, self._stop))
        except Exception as e:  # shown to the user by the calling script
            self.error = e

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()

    def get_new(self):
        items = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                return items


def stream_samples(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Simple blocking generator of (t, n, uv) tuples."""
    s = EEGStream(host, port).start()
    try:
        while True:
            for x in s.get_new():
                yield x.t, x.n, x.uv
            if s.error:
                raise s.error
            threading.Event().wait(0.02)
    finally:
        s.stop()
