"""
MISSION 3: turn a recording into a Neurodata Without Borders (NWB) file.

NWB is the standard format neuroscience labs use to share data, and DANDI is
the archive where those files get published. Converting messy lab formats into
clean NWB is exactly the work CatalystNeuro does.

Input:  recordings/<file>.csv  plus its .json sidecar (written by record.py)
Output: nwb/<file>.nwb

Steps (each TODO is one small piece):
  1. NWBFile with session description, start time, identifier
  2. Subject (you!) with species "Homo sapiens"
  3. Device "PiEEG-8" and an ElectrodeGroup
  4. Electrodes table: one row per channel, with location from the sidecar
  5. ElectricalSeries with the data, rate=250.0, unit conversion to volts
  6. Write it, then validate:  nwbinspector nwb/
  7. Bonus: open it with  pynwb.NWBHDF5IO(...).read()  and replot alpha

Docs: https://pynwb.readthedocs.io  ·  https://nwbinspector.readthedocs.io
Install: pip install pynwb nwbinspector
"""

import json
import sys
from pathlib import Path

import numpy as np

from spectrum import load


def csv_to_nwb(csv_path: Path, out_dir: Path = Path("nwb")) -> Path:
    meta = json.loads(csv_path.with_suffix(".json").read_text())
    data_uv = np.column_stack([load(csv_path, c) for c in range(1, meta["n_channels"] + 1)])

    # TODO 1: nwbfile = NWBFile(...)
    # TODO 2: nwbfile.subject = Subject(...)
    # TODO 3: device = nwbfile.create_device(...); group = nwbfile.create_electrode_group(...)
    # TODO 4: for each channel: nwbfile.add_electrode(...)
    # TODO 5: ElectricalSeries(data=..., electrodes=..., rate=..., conversion=1e-6)
    #         (what does conversion mean, and why 1e-6?)
    # TODO 6: write with NWBHDF5IO
    raise NotImplementedError("Mission 3 is yours. Start at TODO 1.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print("Wrote", csv_to_nwb(Path(sys.argv[1])))
