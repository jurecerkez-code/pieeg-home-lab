"""The other scripts, run the way the README runs them."""

import os

import pytest

from conftest import only_recording, script


@pytest.fixture
def recording(sim, tmp_path):
    r = script("record.py", "--host", "127.0.0.1", "--port", sim, "--seconds", 4, "--label", "rest",
               "--out", tmp_path / "rec", cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    return only_recording(tmp_path / "rec")[0]


def test_self_test(sim, tmp_path):
    r = script("self_test.py", "--host", "127.0.0.1", "--port", sim, "--seconds", 1, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ch8:" in r.stdout and "Device OK" in r.stdout


def test_spectrum(recording, tmp_path):
    r = script("spectrum.py", recording, "--save", tmp_path / "spectrum.png", cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "alpha peak" in r.stdout
    assert (tmp_path / "spectrum.png").stat().st_size > 10_000


def test_mission_1_runs_on_a_raw_recording(recording, tmp_path):
    r = script("mission_1_notch.py", recording, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL hum reduced" in r.stdout          # remove_mains() is still the empty starter
    assert "Note:" not in r.stdout                 # raw data, nothing to warn about


def test_mission_3_starts_as_a_skeleton(recording, tmp_path):
    r = script("mission_3_nwb.py", recording, cwd=tmp_path)
    assert r.returncode != 0
    assert "Mission 3 is yours" in r.stderr


def test_live_view_rejects_channel_0(tmp_path):
    r = script("live_view.py", "--channels", "0", cwd=tmp_path)
    assert r.returncode == 2
    assert "between 1 and 8" in r.stderr


@pytest.mark.skipif(os.environ.get("PIEEG_NETWORK_TESTS") != "1",
                    reason="downloads from GitHub, set PIEEG_NETWORK_TESTS=1")
def test_get_example_data(tmp_path):
    r = script("get_example_data.py", "alpha", "--out", tmp_path / "rec", cwd=tmp_path, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    path, meta = only_recording(tmp_path / "rec")
    assert path.name == "example_alpha.csv"
    assert path.read_text().splitlines()[0] == "t,n,ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8"
    assert meta["n_samples"] > 5000
