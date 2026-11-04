"""Malformed rows must not shift channels or silently change sample timing."""
import numpy as np
import pytest

from conftest import write_recording
from recording import read_recording


def test_interrupted_final_row_is_removed_for_all_channels(tmp_path):
    path = write_recording(tmp_path)
    with path.open("a") as f:
        f.write("0.800,200,1.0")
    rec = read_recording(path)
    assert rec.data.shape == (200, 2)
    assert len(rec.times) == len(rec.numbers) == 200
    assert rec.ignored_trailing_row


@pytest.mark.parametrize("replacement", ["0.040,10,1.0", "0.040,10,nan,2.0", "0.040,10,1.0,oops"])
def test_corrupt_middle_row_is_reported(tmp_path, replacement):
    path = write_recording(tmp_path)
    rows = path.read_text().splitlines()
    rows[11] = replacement
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="row 12"):
        read_recording(path)


def test_clock_jump_backwards_is_not_silently_retimed(tmp_path):
    path = write_recording(tmp_path)
    rows = path.read_text().splitlines()
    rows[11] = "0.0,10,1.0,2.0"
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="go backwards"):
        read_recording(path)


def test_gap_and_filter_boundaries_split_analysis_sections(tmp_path):
    rec = read_recording(write_recording(tmp_path, missing=range(30, 50),
                                        possibly_filtered_samples=[[60, 79]]))
    sections = rec.clean_segments(1)
    assert [len(x) for x in sections] == [30, 10, 120]
    assert all(np.all(np.diff(x) == .5) for x in sections)
