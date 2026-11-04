"""Mission 3: a recording and its sidecar become a clean NWB file."""

import json

import numpy as np
import nwbinspector
import pytest
from pynwb import NWBHDF5IO

from mission_3_nwb import csv_to_nwb
from spectrum import load

from conftest import FS, write_recording


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
        np.testing.assert_allclose(spans, [(30 / FS, 50 / FS), (60 / FS, 80 / FS)])


def test_gap_keeps_its_time_when_counter_starts_above_zero(tmp_path):
    csv_path = write_recording(tmp_path, n=2750, missing=range(2000, 2250),
                               counter_start=1000, time_origin=1793523600.0)
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        nwb = io.read()
        series = nwb.acquisition["eeg"]
        expected = np.r_[np.arange(2000), np.arange(2250, 2750)] / FS
        np.testing.assert_allclose(series.timestamps[:], expected, atol=1e-6)
        assert series.timestamps[-1] == pytest.approx(10.996, abs=1e-6)
        spans = nwb.invalid_times.to_dataframe()
        np.testing.assert_allclose(spans[["start_time", "stop_time"]], [[8, 9]], atol=1e-6)


@pytest.mark.parametrize("bounds, expected", [([None, 1004], (0, .02)),
                                              ([1005, None], (.02, .8)),
                                              ([None, None], (0, .8))])
def test_filter_ranges_with_unknown_boundaries_are_kept(tmp_path, bounds, expected):
    csv_path = write_recording(tmp_path, counter_start=1000, possibly_filtered_samples=[bounds])
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        spans = io.read().invalid_times.to_dataframe()
        np.testing.assert_allclose(spans[["start_time", "stop_time"]], [expected])


def test_calibration_and_original_metadata_survive_export(tmp_path):
    caveat = "Unverified amplitude scale; do not interpret these as calibrated microvolts"
    csv_path = write_recording(tmp_path, units_note=caveat, complete=False,
                               electrodes={"ch1": "Fp1", "ch2": "Fp2", "ref": "Cz", "bias": "M2"})
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        nwb = io.read()
        assert caveat in nwb.acquisition["eeg"].description
        provenance = json.loads(nwb.scratch["recording_provenance"].data)
        assert provenance["sidecar"] == json.loads(csv_path.with_suffix(".json").read_text())
        assert "Reference: Cz" in nwb.electrode_groups["recording_electrodes"].description
        np.testing.assert_array_equal(nwb.scratch["source_sample_numbers"][:], np.arange(200))


def test_counter_restart_does_not_restart_the_nwb_clock(tmp_path):
    csv_path = write_recording(tmp_path, possibly_filtered_samples=[[None, 50]])
    rows = csv_path.read_text().splitlines()
    for i in range(100, 200):
        columns = rows[i + 1].split(",")
        columns[1] = str(i - 100)
        rows[i + 1] = ",".join(columns)
    csv_path.write_text("\n".join(rows) + "\n")
    with NWBHDF5IO(csv_to_nwb(csv_path, tmp_path / "nwb"), "r") as io:
        nwb = io.read()
        np.testing.assert_allclose(nwb.acquisition["eeg"].timestamps[:], np.arange(200) / FS)
        spans = nwb.invalid_times.to_dataframe()
        # The old counter-only filter annotation is ambiguous after a reset.
        assert any("counter reset" in str(tags) for tags in spans["tags"])
        np.testing.assert_allclose(spans[["start_time", "stop_time"]].iloc[-1], [0, .8])


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
