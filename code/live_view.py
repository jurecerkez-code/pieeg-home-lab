"""
Live view of the EEG on your laptop, with a running spectrum.

    python live_view.py                      # real PiEEG on raspberrypi.local
    python live_view.py --host localhost     # together with simulate.py
    python live_view.py --channels 1 2 3     # choose channels (default: 1 2)

Top: last 5 seconds per channel, band-pass filtered 1 to 40 Hz.
Bottom: spectrum of channel 1. Close your eyes and watch the bump at ~10 Hz.
"""

import argparse
import collections

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from scipy import signal

from eeg_stream import EEGStream, SAMPLE_RATE

FS = SAMPLE_RATE
WINDOW_S = 5


def bandpass(x, lo=1.0, hi=40.0):
    sos = signal.butter(4, [lo, hi], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="raspberrypi.local")
    p.add_argument("--channels", type=int, nargs="+", default=[1, 2])
    p.add_argument("--raw", action="store_true", help="show unfiltered signal")
    a = p.parse_args()

    stream = EEGStream(a.host).start()
    n = WINDOW_S * FS
    bufs = {c: collections.deque([0.0] * n, maxlen=n) for c in a.channels}

    fig, axes = plt.subplots(len(a.channels) + 1, 1, figsize=(10, 2 + 1.6 * len(a.channels)))
    fig.canvas.manager.set_window_title(f"PiEEG live: {a.host}")
    tx = np.arange(n) / FS - WINDOW_S
    lines = {}
    for ax, c in zip(axes[:-1], a.channels):
        (lines[c],) = ax.plot(tx, np.zeros(n), lw=0.8)
        ax.set_ylabel(f"ch{c} µV")
        ax.set_xlim(-WINDOW_S, 0)
    axes[-2].set_xlabel("seconds")
    spec_ax = axes[-1]
    f = np.fft.rfftfreq(2 * FS, 1 / FS)
    (spec_line,) = spec_ax.semilogy(f, np.ones_like(f))
    spec_ax.axvspan(8, 13, alpha=0.15, label="alpha 8 to 13 Hz")
    spec_ax.axvline(50, ls=":", lw=1, label="50 Hz mains")
    spec_ax.set_xlim(0, 60)
    spec_ax.set_xlabel("Hz")
    spec_ax.set_ylabel(f"ch{a.channels[0]} power")
    spec_ax.legend(loc="upper right", fontsize=8)
    status = fig.text(0.01, 0.99, "connecting...", va="top", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    def update(_):
        if stream.error:
            status.set_text(f"Error: {stream.error}  (see docs/troubleshooting.md)")
            return
        new = stream.get_new()
        for s in new:
            for c in a.channels:
                if c <= len(s.uv):
                    bufs[c].append(s.uv[c - 1])
        if new:
            warn = stream.channel_warning()
            status.set_text(warn or f"{a.host}   sample #{new[-1].n}")
        for ax, c in zip(axes[:-1], a.channels):
            x = np.asarray(bufs[c])
            y = x - x.mean() if a.raw else bandpass(x)
            lines[c].set_ydata(y)
            lim = max(20.0, np.percentile(np.abs(y), 99) * 1.2)
            ax.set_ylim(-lim, lim)
        x0 = np.asarray(bufs[a.channels[0]])[-2 * FS:]
        ff, pxx = signal.welch(x0 - x0.mean(), fs=FS, nperseg=FS)
        spec_line.set_data(ff, np.maximum(pxx, 1e-6))
        spec_ax.set_xlim(0, 60)
        spec_ax.set_ylim(1e-2, max(10.0, pxx.max() * 2))

    anim = FuncAnimation(fig, update, interval=100, cache_frame_data=False)  # noqa: F841
    plt.show()
    stream.stop()


if __name__ == "__main__":
    main()
