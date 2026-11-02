# From a recording to DANDI

A recording made with this kit is two files: a CSV of channels and a `.json` sidecar written
by [record.py](../code/record.py). Publishing one means turning those two into an NWB file
that passes inspection, and putting that file in a DANDI dataset. This page is the map, and
the honest list of what is still missing.

This is the work [CatalystNeuro](https://catalystneuro.com/) does for research labs: take the
data as the equipment produced it, shape it into NWB, and publish it so it can be read in ten
years.

## 1. Record

```bash
python code/record.py --montage fp1 --seconds 60 --age P29Y --sex F --label rest
```

The sidecar carries what the file needs later: the subject's pseudonym, the electrode
positions, the sample rate, the filtering that really happened, and the ranges where samples
were lost or may have been filtered by another client.

`--age` and `--sex` are optional, and record.py writes them to the sidecar only when they are
given. Whatever is not asked for stays out. The conventions for age and sex are NWB's own:
`P29Y` is an ISO 8601 duration, and a range with a blank bound (`P90Y/`) means open ended.

## 2. Convert to NWB

Two ways, one destination:

```bash
python code/mission_3_nwb.py recordings/2026-11-01_session.csv       # this repository
python code/neuroconv_interface.py recordings/2026-11-01_session.csv nwb/out.nwb   # through NeuroConv
```

Both write the same NWB objects, because both call `mission_3_nwb.add_recording`. What the
file gets:

- the PiEEG-8 as a Device with its maker
- one electrode per channel, carrying the position the sidecar documents and the filtering it
  really had
- the signal as an ElectricalSeries, stored in microvolts and reported in volts through
  `conversion=1e-6`, so the recorded numbers are not rewritten
- the spans a reader should skip as `invalid_times`, with the reason as a tag: a gap in the
  sample counter, or a range another client may have filtered

What is not invented: a subject with no age and no sex in the sidecar gets sex `U` and the open
age range `/`, which is NWB's way of saying it was not recorded.

### About NeuroConv

[NeuroConv](https://github.com/catalystneuro/neuroconv) is the library that turns source
formats into NWB, and `code/neuroconv_interface.py` is one of its data interfaces in shape, so
a recording here goes through the same machinery a research lab uses.

Two things to know before installing it:

- neuroconv 0.10.2 needs Python 3.10 to 3.12. There are no wheels for newer Python.
- it imports only against `zarr` 2.x with `hdmf_zarr` 0.11. With zarr 3 its own import fails
  on `zarr.codec_registry`, before any of this repository's code is reached.

So a working combination is:

```bash
python3.12 -m venv .venv
pip install "zarr==2.18.7" "hdmf_zarr==0.11.0" neuroconv numpy scipy nwbinspector
```

The tests for the interface are skipped when neuroconv is not installed, so the kit itself
does not depend on any of this.

## 3. Inspect

```bash
nwbinspector nwb/
```

[NWB Inspector](https://nwbinspector.readthedocs.io) is what DANDI runs before a file is
accepted. What a converted file from this kit reports today:

- 0 critical issues
- best practice suggestions, because the sidecar does not carry them: experimenter, institution
  and a few descriptions. Those are left out rather than filled in.

## 4. Publish on DANDI

[DANDI](https://dandiarchive.org/) is the archive NWB files are published on. Before this kit's
data could go there, these are missing:

1. **A real recording session with the board.** Nothing here has been recorded with the
   PiEEG-8 yet; see [validation.md](validation.md), part 2.
2. **Consent and ethics.** A recording of a person is human data. DANDI wants a statement about
   consent and whether an ethics review applied. Home recordings of oneself are still worth
   saying so about, in writing.
3. **Real subject metadata** in the sidecar, which `record.py --age --sex` now carries.
4. **The amplitude question settled.** PiEEG Server converts counts to microvolts as
   `4.5 V / 16777215 per count`, and read against the ADS1299 datasheet that is half the true
   value at gain 1. Files keep PiEEG Server's numbers so they stay comparable with its
   dashboard and its example data, and the sidecar says so. A published dataset has to either
   correct that or state it in the dataset description. Silently publishing a known scale error
   is not an option.
5. **A DANDI account and a dataset**, then `dandi download` to check the file from the archive's
   side.

## Where this is tested

- `tests/test_nwb.py`: the converter, the numbers, the marked ranges, the subject
- `tests/test_neuroconv_interface.py`: the same through NeuroConv, skipped without it
- `tests/test_record.py`: the sidecar record.py writes
