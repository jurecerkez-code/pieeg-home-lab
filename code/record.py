"""
Record EEG from PiEEG Server to a CSV file on your laptop.

    python record.py --seconds 60 --label eyes_closed
    python record.py --host localhost --seconds 30      # from simulate.py
    python record.py --subject sub-02 --label eyes_closed   # recording someone else

Writes  recordings/<date>_<subject>_<label>.csv   with columns: t, n, ch1 ... ch8
and a small  .json  next to it with the settings (useful later for NWB).
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from eeg_stream import EEGStream, SAMPLE_RATE


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="raspberrypi.local")
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--label", default="session")
    p.add_argument("--out", default="recordings")
    p.add_argument("--subject", default="sub-01",
                   help="pseudonym of the person recorded, never a real name (sub-01, sub-02, ...)")
    a = p.parse_args()

    out = Path(a.out)
    out.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out / f"{stamp}_{a.subject}_{a.label}.csv"

    stream = EEGStream(a.host).start()
    print(f"Recording {a.seconds:.0f} s from {a.host} ... (Ctrl+C stops early)")
    rows, first_n, n_ch, t0 = [], None, None, time.time()
    try:
        while time.time() - t0 < a.seconds + 2:
            for s in stream.get_new():
                if first_n is None:
                    first_n, n_ch = s.n, len(s.uv)
                rows.append([s.t, s.n, *s.uv])
                if len(rows) >= a.seconds * SAMPLE_RATE:
                    break
            if stream.error:
                raise SystemExit(f"Could not read from {stream.url}: {stream.error}")
            if len(rows) >= a.seconds * SAMPLE_RATE:
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    stream.stop()
    if stream.channel_warning():
        print("Warning:", stream.channel_warning())

    if not rows:
        raise SystemExit("No samples received. Is PiEEG Server running? See docs/troubleshooting.md")

    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "n", *[f"ch{i}" for i in range(1, n_ch + 1)]])
        w.writerows(rows)

    gaps = sum(1 for a_, b_ in zip(rows, rows[1:]) if b_[1] - a_[1] != 1)
    meta = {
        "label": a.label, "subject": a.subject, "start_time": datetime.fromtimestamp(rows[0][0]).isoformat(),
        "sample_rate_hz": SAMPLE_RATE, "n_samples": len(rows), "n_channels": n_ch,
        "units": "microvolts", "source": f"PiEEG Server @ {a.host}",
        "dropped_sample_gaps": gaps,
        "electrodes": {"ch1": "Fp1 (left forehead)", "ref": "left mastoid", "bias": "right mastoid"},
    }
    csv_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {len(rows)} samples ({len(rows)/SAMPLE_RATE:.1f} s) to {csv_path}")
    if gaps:
        print(f"Note: {gaps} gap(s) in sample numbers, some samples were dropped on the way.")


if __name__ == "__main__":
    main()
