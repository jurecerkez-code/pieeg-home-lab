"""PiEEGInterface against neuroconv: the recording converts through their machinery and the
recorded numbers survive the round trip.

These tests are skipped when neuroconv is not installed, which is the default here. neuroconv
is an extra for this kit, not a dependency of it. To run them, use a Python that can install
neuroconv (3.10 to 3.12) and install neuroconv, numpy, scipy, pytest and nwbinspector.
"""

import numpy as np
import pytest
from pynwb import NWBHDF5IO

pytest.importorskip("neuroconv")

from conftest import FS, write_recording
from neuroconv_interface import PiEEGInterface
from spectrum import load


def test_the_source_is_a_recording_csv():
    schema = PiEEGInterface.get_source_schema()
    assert schema["required"] == ["file_path"]
    assert PiEEGInterface.associated_suffixes == (".csv",)


def test_metadata_reports_what_the_sidecar_knows(tmp_path):
    csv_path = write_recording(tmp_path, subject_age="P29Y", subject_sex="F", label="rest")
    metadata = PiEEGInterface(str(csv_path)).get_metadata()
    assert metadata["Subject"]["subject_id"] == "sub-02"
    assert metadata["Subject"]["age"] == "P29Y"
    assert metadata["Subject"]["sex"] == "F"
    assert metadata["NWBFile"]["session_id"] == "rest"
    assert metadata["NWBFile"]["session_start_time"] == "2026-11-01T10:00:00+01:00"


def test_an_unknown_subject_is_left_unknown(tmp_path):
    """What record.py was never told is not invented: NWB's unknown forms."""
    metadata = PiEEGInterface(str(write_recording(tmp_path))).get_metadata()
    assert metadata["Subject"]["sex"] == "U"
    assert metadata["Subject"]["age"] == "/"


def test_conversion_keeps_the_recorded_numbers(tmp_path):
    csv_path = write_recording(tmp_path, missing=range(30, 50))
    out = tmp_path / "out.nwb"
    PiEEGInterface(str(csv_path)).run_conversion(nwbfile_path=out, overwrite=True)
    with NWBHDF5IO(out, "r") as io:
        nwb = io.read()
        series = nwb.acquisition["eeg"]
        from_csv = np.column_stack([load(csv_path, c) for c in (1, 2)])
        expected_times = np.r_[np.arange(30), np.arange(50, 200)] / FS
        np.testing.assert_allclose(series.timestamps[:], expected_times)
        assert series.conversion == 1e-6        # microvolts stored, volts reported
        assert np.allclose(series.data[:] * series.conversion, from_csv * 1e-6)
        assert list(nwb.electrodes["location"]) == ["Fp1, left forehead", "Fp2, right forehead"]
        spans = list(zip(nwb.intervals["invalid_times"]["start_time"][:],
                         nwb.intervals["invalid_times"]["stop_time"][:]))
        np.testing.assert_allclose(spans, [(30 / FS, 50 / FS)])


def test_a_recording_without_a_sidecar_is_refused(tmp_path):
    lonely = tmp_path / "lonely.csv"
    lonely.write_text("t,n,ch1\n0.0,0,0.0\n")
    with pytest.raises(FileNotFoundError):
        PiEEGInterface(str(lonely))


def test_the_metadata_passes_neuroconvs_own_schema(tmp_path):
    interface = PiEEGInterface(str(write_recording(tmp_path, subject_age="P29Y", subject_sex="F")))
    interface.validate_metadata(metadata=interface.get_metadata())


def test_a_recording_without_a_start_time_still_converts(tmp_path):
    """PiEEG's own example recordings carry no start time, and NeuroConv requires one."""
    csv_path = write_recording(tmp_path, start_time=None)
    metadata = PiEEGInterface(str(csv_path)).get_metadata()
    assert metadata["NWBFile"]["session_start_time"]
    assert "start time unknown" in metadata["NWBFile"]["session_description"]
