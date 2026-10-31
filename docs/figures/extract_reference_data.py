"""
Extract the reference data the figures are drawn from, so every coordinate in them
has a published source. Run once; make_figures.py only reads the JSON files it writes.

    pip install mne ezdxf pandas openpyxl scipy
    python extract_reference_data.py

1. Electrode positions: MNE-Python's standard 10-20 montage (head coordinates, mm).
2. Raspberry Pi 3 Model B top view: Raspberry Pi Ltd's official mechanical drawing
   (DXF, RPI-3B-V1_2), board outline, component outlines and the 40 pin header.
3. The EEG trace in the README banner: 6 s of PiEEG's published example recording
   output3.xlsx, channel 8, 1 to 40 Hz, where it shows a clear alpha rhythm.
"""

import json
import math
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DXF_URL = ("https://pip-assets.raspberrypi.com/categories/520-raspberry-pi-3-model-b/documents/"
           "RP-008334-DS-1-raspberry-pi-3-b-mechanical-drawing.dxf")

CHANNELS = ["Fp1", "Fpz", "Fp2", "AFz", "F7", "F3", "Fz", "F4", "F8", "FCz", "T7", "C3", "Cz", "C4", "T8", "CPz", "POz",
            "P7", "P3", "Pz", "P4", "P8", "O1", "Oz", "O2", "Iz", "M1", "M2", "A1", "A2", "TP9", "TP10"]


def electrodes():
    import mne
    name = "colin27_1020" if "colin27_1020" in mne.channels.get_builtin_montages() else "standard_1020"
    montage = mne.channels.make_standard_montage(name)
    pos = montage.get_positions()
    out = {"source": f"MNE-Python {mne.__version__}, make_standard_montage('{name}')",
           "units": "mm, MNE head coordinates: x to the right ear, y to the nose, z up",
           "fiducials": {k: [round(float(v) * 1000, 2) for v in pos[k]] for k in ("nasion", "lpa", "rpa")},
           "channels": {c: [round(float(v) * 1000, 2) for v in pos["ch_pos"][c]] for c in CHANNELS}}
    (DATA / "electrodes_1020.json").write_text(json.dumps(out, indent=1))


def bulge_points(p0, p1, bulge, n=8):
    """Points along a DXF polyline arc segment (bulge = tan(angle / 4))."""
    if abs(bulge) < 1e-9:
        return [p1]
    (x0, y0), (x1, y1) = p0, p1
    ang = 4 * math.atan(bulge)
    chord = math.hypot(x1 - x0, y1 - y0)
    r = chord / (2 * math.sin(ang / 2))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    d = math.sqrt(max(r * r - (chord / 2) ** 2, 0)) * (1 if bulge > 0 else -1)
    cx, cy = mx - d * (y1 - y0) / chord, my + d * (x1 - x0) / chord
    a0 = math.atan2(y0 - cy, x0 - cx)
    return [(cx + abs(r) * math.cos(a0 + ang * k / n), cy + abs(r) * math.sin(a0 + ang * k / n)) for k in range(1, n + 1)]


def raspberry_pi():
    import ezdxf
    path = DATA / "raspberry-pi-3-b-mechanical-drawing.dxf"
    if not path.exists():
        urllib.request.urlretrieve(DXF_URL, path)
    msp = ezdxf.readfile(path).modelspace()

    def poly(e):
        vs = list(e.vertices)
        pts = [(vs[0].dxf.location.x, vs[0].dxf.location.y)]
        for a, b in zip(vs, vs[1:] + ([vs[0]] if e.is_closed else [])):
            pts += bulge_points((a.dxf.location.x, a.dxf.location.y), (b.dxf.location.x, b.dxf.location.y), a.dxf.bulge)
        return [[round(x, 3), round(y, 3)] for x, y in pts]

    outline = [poly(e) for e in msp if e.dxf.layer == "BOARD_OUTLINE"][0]
    parts = [poly(e) for e in msp if e.dxftype() == "POLYLINE" and e.dxf.layer == "PARTS_TOP"]
    pins = [[round(e.dxf.center.x, 3), round(e.dxf.center.y, 3)] for e in msp
            if e.dxftype() == "CIRCLE" and e.dxf.layer == "PINS_TOP" and abs(e.dxf.radius - 0.8) < 1e-6
            and 7 < e.dxf.center.x < 58 and 49.5 < e.dxf.center.y < 55.5]
    pins.append([8.37, 51.23])  # pin 1 is drawn as a square pad (7.57..9.17, 50.43..52.03)
    bottom = []
    for e in msp:
        if e.dxftype() == "POLYLINE" and e.dxf.layer == "PARTS_BOTTOM":
            q = poly(e)
            xs, ys = [a for a, b in q], [b for a, b in q]
            if (max(xs) - min(xs)) * (max(ys) - min(ys)) > 40:
                bottom.append([round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)])
    out = {"source": "Raspberry Pi Ltd, Raspberry Pi 3 Model B mechanical drawing RPI-3B-V1_2 (DXF), " + DXF_URL,
           "parts_bottom_boxes": bottom,
           "units": "mm, origin at the board's bottom left corner, y up, top view",
           "outline": outline, "parts_top": parts, "gpio_pins": sorted(pins), "gpio_pin1": [8.37, 51.23],
           "mounting_holes": {"centers": [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]], "diameter": 2.75},
           "heights_mm": {"gpio_header": 8.5, "usb": 16.0, "ethernet": 13.5, "hdmi": 6.5, "audio": 6.0}}
    (DATA / "raspberry_pi_3b.json").write_text(json.dumps(out, separators=(",", ":")))


def hero_trace():
    import io
    import numpy as np
    import pandas as pd
    from scipy import signal
    url = "https://raw.githubusercontent.com/pieeg-club/PiEEG-8/main/1.GUI/dataset/output3.xlsx"
    raw = pd.read_excel(io.BytesIO(urllib.request.urlopen(url, timeout=60).read())).iloc[:, :8].to_numpy(float)
    fs, ch, t0, t1 = 250, 8, 30.0, 36.0
    x = raw[:, ch - 1] - raw[:, ch - 1].mean()
    y = signal.sosfiltfilt(signal.butter(4, [1, 40], btype="band", fs=fs, output="sos"), x)
    seg = y[int(t0 * fs):int(t1 * fs)]
    f, p = signal.welch(seg, fs=fs, nperseg=2 * fs)
    band = (f >= 8) & (f <= 13)
    out = {"source": url, "channel": ch, "start_s": t0, "end_s": t1, "sample_rate_hz": fs,
           "filter": "Butterworth bandpass 1 to 40 Hz, order 4, zero phase (sosfiltfilt)",
           "alpha_peak_hz": round(float(f[band][np.argmax(p[band])]), 1),
           "microvolts": [round(float(v), 2) for v in seg]}
    (DATA / "hero_trace.json").write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    electrodes()
    raspberry_pi()
    hero_trace()
    print("wrote", *sorted(p.name for p in DATA.glob("*.json")))
