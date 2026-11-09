"""Read a recording once, keeping every channel on the same source timeline."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Recording:
    data: np.ndarray
    source_times: np.ndarray
    numbers: np.ndarray
    meta: dict
    fs: float
    ignored_trailing_row: bool = False

    @property
    def times(self):
        return self.source_times - self.source_times[0]

    @property
    def end(self):
        return float(self.times[-1] + 1 / self.fs)

    @property
    def breaks(self):
        # A long timestamp step can reveal a pause even when the server's counter
        # did not advance. Software timestamps can also jitter; do not bridge it.
        return (np.diff(self.numbers) != 1) | (np.diff(self.source_times) > 1.5 / self.fs)

    def nwb_timing(self):
        uniform = np.arange(len(self.data)) / self.fs
        if not self.breaks.any() and np.allclose(self.times, uniform, atol=1e-6, rtol=0):
            return {"starting_time": 0.0, "rate": self.fs}
        return {"timestamps": self.times}

    def invalid_intervals(self):
        """Intervals in seconds from the first saved sample, like the EEG series."""
        out, times = [], self.times
        for i in np.flatnonzero(self.breaks):
            start, stop = times[i] + 1 / self.fs, times[i + 1]
            reason = "gap in recorded samples"
            if self.numbers[i + 1] <= self.numbers[i] or stop <= start:
                start, stop = times[i], times[i + 1] + 1 / self.fs
                reason = "sample counter discontinuity; timing around the boundary is uncertain"
            out.append((float(start), float(stop), reason))

        ranges = self.meta.get("possibly_filtered_samples") or []
        if ranges and np.any(np.diff(self.numbers) <= 0):
            # Old sidecars identify ranges only by counter, which becomes
            # ambiguous after a restart. Exclude the whole recording conservatively.
            out.append((0.0, self.end, "possibly filtered; counter reset prevents locating the affected samples"))
        else:
            for first, last in ranges:
                if first is not None and last is not None and last < first:
                    raise ValueError("A possibly filtered range ends before it starts")
                mask = np.ones(len(times), dtype=bool)
                if first is not None:
                    mask &= self.numbers >= first
                if last is not None:
                    mask &= self.numbers <= last
                ix = np.flatnonzero(mask)
                if len(ix):
                    out.append((float(times[ix[0]]), float(times[ix[-1]] + 1 / self.fs),
                                "possibly filtered by another client during the recording"))
        return out

    def clean_segments(self, channel):
        """Contiguous channel arrays, excluding all marked invalid intervals."""
        if not 1 <= channel <= self.data.shape[1]:
            raise ValueError(f"Choose a channel between 1 and {self.data.shape[1]}")
        valid = np.ones(len(self.data), dtype=bool)
        for start, stop, _ in self.invalid_intervals():
            valid &= ~((self.times >= start) & (self.times < stop))
        boundaries = np.r_[0, np.flatnonzero(self.breaks) + 1, len(self.data)]
        out = []
        for a, b in zip(boundaries[:-1], boundaries[1:]):
            edges = np.flatnonzero(np.diff(np.r_[False, valid[a:b], False]))
            for left, right in zip(edges[::2], edges[1::2]):
                out.append(self.data[a + left:a + right, channel - 1])
        return out


def read_recording(path):
    path = Path(path)
    meta = json.loads(path.with_suffix(".json").read_text())
    fs = float(meta["sample_rate_hz"])
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("The sidecar must give a positive, finite sample_rate_hz")
    channels = int(meta["n_channels"])
    if channels < 1:
        raise ValueError("The recording must contain at least one channel")
    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError("The recording is empty")
    header, rows = rows[0], rows[1:]
    required = ["t", "n", *[f"ch{i}" for i in range(1, channels + 1)]]
    if len(set(header)) != len(header) or any(name not in header for name in required):
        raise ValueError("CSV needs unique t, n and channel columns matching its sidecar")
    cols = [header.index(name) for name in required]
    data, times, numbers, ignored = [], [], [], False
    for i, row in enumerate(rows):
        if len(row) != len(header):
            if i == len(rows) - 1 and len(row) < len(header):
                ignored = True  # interrupted final write; all channels lose the same row
                continue
            raise ValueError(f"Malformed CSV row {i + 2}; no channels were silently shifted")
        try:
            t = float(row[cols[0]])
            n = int(row[cols[1]])
            values = [float(row[c]) for c in cols[2:]]
        except ValueError as exc:
            raise ValueError(f"Non-numeric data in CSV row {i + 2}") from exc
        if n < 0 or not np.isfinite([t, *values]).all():
            raise ValueError(f"Invalid or non-finite data in CSV row {i + 2}")
        times.append(t)
        numbers.append(n)
        data.append(values)
    if not data:
        raise ValueError("The recording contains no complete samples")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Recording timestamps repeat or go backwards; cannot place samples reliably in time")
    return Recording(np.asarray(data), np.asarray(times), np.asarray(numbers, dtype=np.int64), meta, fs, ignored)
