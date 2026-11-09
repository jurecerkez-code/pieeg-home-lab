"""
Look for a clear alpha rhythm in a recording.

    python spectrum.py recordings/20261225_190000_eyes_open.csv recordings/20261225_190130_eyes_closed.csv

Plots the power spectrum (Welch) of each file for one channel and prints
candidate alpha peak and alpha power. "No clear alpha rhythm detected" is a valid
result. A candidate is a spectral feature, not proof of a brain state.
"""

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from recording import read_recording

FS = 250


def load(path, channel):
    """One channel of a recording as a NumPy array (µV). Skips an incomplete last line."""
    with open(path) as f:
        r = csv.reader(f)
        header = next(r)
        col = header.index(f"ch{channel}")
        values = []
        for row in r:
            if len(row) != len(header):
                continue
            try:
                values.append(float(row[col]))
            except ValueError:
                continue
        return np.array(values)


def sidecar_notes(path):
    """Warnings from the .json sidecar that change how to read the spectrum."""
    side = Path(path).with_suffix(".json")
    if not side.exists():
        return []
    try:
        meta = json.loads(side.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    notes = []
    filtering = str(meta.get("data_filtering", "none"))
    if not filtering.startswith("none"):
        notes.append("recorded WITH PiEEG Server filters, not raw")
    if meta.get("possibly_filtered_samples"):
        notes.append("part of it may be filtered; spectrum.py excludes the marked ranges")
    if meta.get("missing_samples"):
        notes.append(f"{meta['missing_samples']} samples missing; spectrum.py analyzes continuous sections separately")
    if meta.get("complete") is False:
        notes.append("incomplete recording; check end_reason and unrecorded_duration_s in the sidecar")
    if meta.get("units_note"):
        notes.append(str(meta["units_note"]))
    return notes


def _psd(x, fs):
    if not np.isfinite(fs) or fs <= 80:
        raise ValueError("The 1–40 Hz analysis needs a sample rate greater than 80 Hz")
    if len(x) < round(2 * fs):
        raise ValueError("Need at least 2 seconds of continuous data for a spectrum")
    if not np.isfinite(x).all():
        raise ValueError("The signal contains invalid values")
    sos = signal.butter(4, [1, 40], btype="band", fs=fs, output="sos")
    x = signal.sosfiltfilt(sos, x - x.mean())
    return signal.welch(x, fs=fs, nperseg=round(2 * fs))


def _alpha_summary(f, p):
    """Conservative teaching heuristic, not a validated oscillation detector.

    Require a local maximum with >=3 dB prominence and >=6 dB above a smooth
    log-log background fitted at 3–7 and 14–30 Hz. Never pick a bin just because
    it is the largest in the alpha band. Bin spacing is not measurement accuracy.
    """
    band = (f >= 8) & (f <= 13)
    power = np.trapezoid(p[band], f[band])
    peak = None
    if p.max() > 0:
        floor = max(float(p.max()) * 1e-12, np.finfo(float).tiny)
        db = 10 * np.log10(np.maximum(p, floor))
        background = ((f >= 3) & (f <= 7)) | ((f >= 14) & (f <= 30))
        fit = np.polyfit(np.log10(f[background]), db[background], 1)
        candidates, _ = signal.find_peaks(db, prominence=3)
        candidates = candidates[band[candidates]]
        if len(candidates):
            above = db[candidates] - np.polyval(fit, np.log10(f[candidates]))
            candidates = candidates[above >= 6]
            if len(candidates):
                peak = float(f[candidates[np.argmax(p[candidates])]])
    return peak, float(power)


def alpha_stats(x, fs=FS):
    """A continuous array: Welch spectrum, candidate peak (or None), band power."""
    f, p = _psd(np.asarray(x), fs)
    peak, power = _alpha_summary(f, p)
    return f, p, peak, power


def recording_stats(path, channel):
    """Average spectra of valid sections; filtering never crosses a gap."""
    recording = read_recording(path)
    spectra, weights, used = [], [], 0
    nperseg = round(2 * recording.fs)
    for x in recording.clean_segments(channel):
        if len(x) < nperseg:
            continue
        f, p = _psd(x, recording.fs)
        spectra.append(p)
        weights.append(1 + (len(x) - nperseg) // (nperseg - nperseg // 2))
        used += len(x)
    if not spectra:
        raise ValueError("No usable continuous section of at least 2 seconds remains")
    p = np.average(spectra, axis=0, weights=weights)
    peak, power = _alpha_summary(f, p)
    return f, p, peak, power, used / recording.fs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--save", help="save the figure instead of showing it")
    a = ap.parse_args()

    fig, ax = plt.subplots(figsize=(8, 4))
    for path in a.files:
        try:
            f, p, peak, power, used_s = recording_stats(path, a.channel)
        except (ValueError, OSError, KeyError) as exc:
            ap.error(f"{path}: {exc}")
        name = Path(path).stem
        result = "No clear alpha rhythm detected" if peak is None else f"candidate alpha peak {peak:.1f} Hz"
        print(f"{name:40s} {result}; alpha power {power:.1f} µV²; {used_s:.1f} s analyzed")
        for note in sidecar_notes(path):
            print(f"{'':40s} note: {note}")
        # A zero spectrum has no logarithm; keep the plot readable without inventing a peak.
        ax.semilogy(f, np.maximum(p, np.finfo(float).tiny), label=f"{name} ({result})")
    ax.axvspan(8, 13, alpha=0.12)
    ax.set_xlim(0, 45)
    ax.set_xlabel("Hz")
    ax.set_ylabel("µV²/Hz")
    ax.set_title(f"Power spectrum, ch{a.channel}")
    ax.legend(fontsize=8)
    fig.text(0.5, 0.01, "Candidate peaks need visual checking for artifacts. Amplitudes use the source's scale.",
             ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    if a.save:
        fig.savefig(a.save, dpi=130)
        print(f"Saved {a.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
