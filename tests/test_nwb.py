"""Mission 3: a recording and its sidecar become a clean NWB file."""

import json

import numpy as np
import nwbinspector
from pynwb import NWBHDF5IO

from mission_3_nwb import csv_to_nwb
from spectrum import load

FS = 250


def write_recording(tmp_path, n=200, missing=None, **sidecar):
    """A CSV plus sidecar in record.py's format. missing holds sample counter
    ranges that were never recorded."""
    missing = set(missing or [])
    ns = [i for i in range(n) if i not in missing]
    csv_path = tmp_path / "session.csv"
    with open(csv_path, "w") as f:
        f.write("t,n,ch1,ch2\n")
        for k, i in enumerate(ns):
            f.write(f"{i / FS:.3f},{i},{k * 0.5:.2f},{k * -0.5:.2f}\n")
    meta = {
        "label": "rest",
        "subject": "sub-02",
        "notes": "sat still",
        "start_time": "2026-11-01T10:00:00+01:00",
        "sample_rate_hz": FS,
        "n_samples": len(ns),
        "n_channels": 2,
        "units": "microvolts",
        "electrodes": {"ch1": "Fp1, left forehead", "ch2": "Fp2, right forehead",
                       "ref": "M1, left mastoid", "bias": "M2, right mastoid"},
        "data_filtering": "none: record.py kept PiEEG Server's filters off",
    }
    meta.update(sidecar)
    csv_path.with_suffix(".json").write_text(json.dumps(meta))
    return csv_path


def test_the_file_reads_back_with_the_same_numbers(tmp_path):
    csv_path = write_recording(tmp_path)
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        nwb = io.read()
        series = nwb.acquisition["eeg"]
        from_csv = np.column_stack([load(csv_path, c) for c in (1, 2)])
        assert series.rate == FS
        assert series.unit == "volts" and series.conversion == 1e-6     # microvolts stored, volts reported
        assert np.allclose(series.data[:] * series.conversion, from_csv * 1e-6)
        assert series.filtering.startswith("none:")
        assert len(nwb.electrodes) == 2
        assert list(nwb.electrodes["location"]) == ["Fp1, left forehead", "Fp2, right forehead"]
        assert nwb.session_start_time.utcoffset() is not None           # NWB requires a time zone


def test_gaps_and_maybe_filtered_ranges_are_marked(tmp_path):
    csv_path = write_recording(tmp_path, missing=range(30, 50),
                               possibly_filtered_samples=[[60, 79]])
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        rows = io.read().intervals["invalid_times"]
        spans = list(zip(rows["start_time"][:], rows["stop_time"][:]))
        assert (30 / FS, 50 / FS) in spans      # samples 30 to 49 never arrived
        assert (60 / FS, 80 / FS) in spans      # samples 60 to 79 may have been filtered


def test_subject_takes_what_the_sidecar_knows(tmp_path):
    csv_path = write_recording(tmp_path, subject_age="P29Y", subject_sex="F")
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        subject = io.read().subject
        assert (subject.subject_id, subject.age, subject.sex) == ("sub-02", "P29Y", "F")


def test_unknown_subject_still_passes_the_inspector(tmp_path):
    csv_path = write_recording(tmp_path)            # no age, no sex in the sidecar
    out = csv_to_nwb(csv_path, tmp_path / "nwb")
    with NWBHDF5IO(out, "r") as io:
        subject = io.read().subject
        assert subject.sex == "U"                   # NWB's word for unknown
        assert subject.age == "/"                   # open range: no lower or upper bound
    critical = [m for m in nwbinspector.inspect_all(out, progress_bar=False)
                if m and m.importance.name == "CRITICAL"]
    assert critical == []
