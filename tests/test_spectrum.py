"""Known signals and missing data exercise scientific interpretation, not just file creation."""
import json

import numpy as np
import pytest

from spectrum import alpha_stats, recording_stats


def test_flat_signal_has_no_alpha_peak():
    assert alpha_stats(np.zeros(2500))[2:] == (None, 0.0)
    assert alpha_stats(np.full(2500, 20.0))[2:] == (None, 0.0)


def test_broadband_noise_has_no_clear_alpha_peak():
    noise = np.random.default_rng(52).normal(size=250 * 60)
    assert alpha_stats(noise)[2] is None


@pytest.mark.parametrize("fs", [250, 500])
def test_known_rhythm_has_correct_frequency(fs):
    t = np.arange(10 * fs) / fs
    assert alpha_stats(12 * np.sin(2 * np.pi * 11 * t), fs=fs)[2] == 11


def test_short_and_invalid_data_are_reported():
    with pytest.raises(ValueError, match="2 seconds"):
        alpha_stats(np.zeros(100))
    with pytest.raises(ValueError, match="invalid values"):
        alpha_stats(np.full(1000, np.nan))


def test_analysis_does_not_filter_across_a_gap_and_uses_sidecar_rate(tmp_path):
    # Two constant sections with a large voltage step at a gap contain no rhythm.
    # Filtering a concatenated array would manufacture a transient at that step.
    fs = 500
    ns = np.r_[np.arange(1500), np.arange(2000, 3500)]
    path = tmp_path / "gap.csv"
    with path.open("w") as f:
        f.write("t,n,ch1\n")
        for n in ns:
            f.write(f"{n/fs},{n},{100 if n < 1500 else -100}\n")
    path.with_suffix(".json").write_text(json.dumps({"n_channels": 1, "sample_rate_hz": fs}))
    frequencies, power, peak, alpha_power, seconds = recording_stats(path, 1)
    assert peak is None and alpha_power == 0
    assert np.all(power == 0)
    assert seconds == 6 and frequencies[-1] == 250
