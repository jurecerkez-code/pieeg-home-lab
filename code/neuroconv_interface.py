"""PiEEGInterface: one recording from this kit as NWB, in NeuroConv's shape.

NeuroConv (https://github.com/catalystneuro/neuroconv) turns neuroscience source formats into
NWB, and every one of its data interfaces looks the same: construct it with the path to one
recording, ask it for metadata, then convert. This is such an interface, so a recording made
with this kit goes through the same tools a research lab uses instead of only through this
repository's own converter.

The two ways in are one recording each:

    from neuroconv_interface import PiEEGInterface
    interface = PiEEGInterface("recordings/2026-11-01_session.csv")
    interface.run_conversion("nwb/2026-11-01_session.nwb")

    python neuroconv_interface.py recordings/2026-11-01_session.csv nwb/out.nwb

The sidecar written by record.py is the source of every value, exactly as in
code/mission_3_nwb.py. Both call mission_3_nwb.add_recording, so the file holds the same
electrodes, the same microvolts reported as volts and the same ranges to skip.

Needs neuroconv (pip install neuroconv). Note that neuroconv 0.10.2 only imports against
zarr 2.x and hdmf_zarr 0.11, and needs Python 3.10 to 3.12; on newer Python or zarr 3 its
import fails before this file is reached. This module raises a clear error in that case.
"""

import json
import sys
from pathlib import Path

import numpy as np

try:
    from neuroconv.basedatainterface import BaseDataInterface
except ImportError as exc:
    raise ImportError(
        "code/neuroconv_interface.py needs the neuroconv package: pip install neuroconv"
    ) from exc

from mission_3_nwb import add_recording, start_time
from spectrum import load


class PiEEGInterface(BaseDataInterface):
    """One recording from the PiEEG-8 shield: a CSV of channels and its .json sidecar."""

    display_name = "PiEEG recording"
    associated_suffixes = (".csv",)
    keywords = ("EEG", "PiEEG-8", "Raspberry Pi", "ADS1299", "biopotential", "home lab")
    info = "Interface for writing a recording from the PiEEG-8 shield as NWB."

    def __init__(self, file_path: str, verbose: bool = False):
        file_path = Path(file_path)
        sidecar = file_path.with_suffix(".json")
        if not file_path.exists():
            raise FileNotFoundError(f"no such recording: {file_path}")
        if not sidecar.exists():
            raise FileNotFoundError(f"the recording has no sidecar: {sidecar}")
        self.file_path = file_path
        self.verbose = verbose
        self._meta = json.loads(sidecar.read_text())
        self._n_channels = int(self._meta["n_channels"])
        self._fs = float(self._meta["sample_rate_hz"])

    def get_metadata(self) -> dict:
        """What the sidecar knows: the session and the subject, nothing invented.

        A recording made without --age or --sex has neither, and then the subject carries
        sex "U" and the open age range "/", NWB's way of saying it was not recorded.

        NeuroConv requires a session start time. PiEEG's own example recordings carry none,
        so the conversion time stands in and the session description says so, the same way
        code/mission_3_nwb.py handles it.
        """
        meta = self._meta
        start = start_time(meta)
        described = meta.get("description") or meta.get("label", "PiEEG recording")
        if not meta.get("start_time"):
            described += " (start time unknown: set to the conversion time)"
        metadata = {
            "NWBFile": {
                "session_description": described,
                "session_start_time": start.isoformat(),
                "session_id": meta.get("label", "session"),
                "identifier": f"pieeg-home-lab:{meta.get('label', 'session')}:{start.isoformat()}",
            },
            "Subject": {
                "subject_id": str(meta.get("subject", "sub-01")),
                "species": "Homo sapiens",
                "description": "Recorded at home with the PiEEG Home Lab kit",
                "sex": str(meta.get("subject_sex", "U")).upper(),
                "age": str(meta.get("subject_age", "/")),
            },
        }
        notes = str(meta.get("notes", "") or "")
        if notes:
            metadata["NWBFile"]["experiment_description"] = notes
        metadata["NWBFile"]["keywords"] = list(self.keywords[:5])
        return metadata

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, **conversion_options) -> None:
        """Add the shield, its electrodes and the signal to the file being built."""
        data_uv = np.column_stack(
            [load(self.file_path, c) for c in range(1, self._n_channels + 1)])
        add_recording(nwbfile, data_uv, self._meta, self.file_path, self._fs, self._n_channels)
        if self.verbose:
            print(f"added {self._n_channels} channels of {len(data_uv)} samples from {self.file_path}")


def main() -> None:
    """Convert one recording through NeuroConv, the way this interface is meant to be used."""
    if len(sys.argv) != 3:
        raise SystemExit("usage: python neuroconv_interface.py recording.csv out.nwb")
    from pynwb import NWBHDF5IO

    interface = PiEEGInterface(sys.argv[1], verbose=True)
    out = Path(sys.argv[2])
    if out.suffix != ".nwb":
        raise SystemExit("the output has to end in .nwb")
    out.parent.mkdir(parents=True, exist_ok=True)
    interface.run_conversion(nwbfile_path=out, overwrite=True)
    print("Wrote", out)
    with NWBHDF5IO(out, "r") as io:
        nwbfile = io.read()
        print(f"{len(nwbfile.acquisition['eeg'].data)} samples, "
              f"{nwbfile.acquisition['eeg'].data.shape[1]} channels")


if __name__ == "__main__":
    main()
