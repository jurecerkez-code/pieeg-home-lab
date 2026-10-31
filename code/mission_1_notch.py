"""
MISSION 1: kill the 50 Hz hum.

Every wall socket in Berlin runs at 50 Hz, and your body picks it up like an
antenna. In the raw signal it can be bigger than your brain waves.

Your job: write remove_mains() so the 50 Hz peak disappears from the spectrum
but the alpha peak (8 to 13 Hz) stays untouched.

Test it:
    python mission_1_notch.py recordings/<your_file>.csv

Done when: the script prints PASS for both checks.

Hints, only if you want them:
  - scipy.signal.iirnotch(w0=50, Q=..., fs=250) and filtfilt
  - what happens at 100 Hz? (harmonics, and also: what is Nyquist here?)
  - bonus: compare a notch with simply low-passing at 40 Hz. When is each better?
"""

import sys

import numpy as np
from scipy import signal

from spectrum import load

FS = 250


def remove_mains(x: np.ndarray) -> np.ndarray:
    # TODO: your code here
    return x


def band_power(x, lo, hi):
    f, p = signal.welch(x - x.mean(), fs=FS, nperseg=2 * FS)
    m = (f >= lo) & (f <= hi)
    return np.trapezoid(p[m], f[m])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    x = load(sys.argv[1], channel=1)
    y = remove_mains(x)
    hum_before, hum_after = band_power(x, 49, 51), band_power(y, 49, 51)
    a_before, a_after = band_power(x, 8, 13), band_power(y, 8, 13)
    print(f"50 Hz power: {hum_before:10.2f} -> {hum_after:10.2f}")
    print(f"alpha power: {a_before:10.2f} -> {a_after:10.2f}")
    ok1 = hum_after < 0.05 * hum_before
    ok2 = abs(a_after - a_before) < 0.1 * a_before
    print("PASS" if ok1 else "FAIL", "hum reduced by more than 95 %")
    print("PASS" if ok2 else "FAIL", "alpha changed by less than 10 %")
