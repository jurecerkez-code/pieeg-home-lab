# Missions

Each mission is small enough for one evening. Do them in order or not, they're yours. Every mission works on your own recordings, on someone else's ([recording someone else](recording-someone-else.md)), or on PiEEG's published example data.

---

## Mission 0: real data first

Before anyone wears electrodes, work with real PiEEG recordings. PiEEG publishes three example files from their own hardware. One command downloads them and converts them to this repo's format:

```bash
python get_example_data.py
python spectrum.py recordings/example_*.csv
```

| File | What's in it |
|---|---|
| `example_dry.csv` | 77 s, 8 channels, dry Ag/AgCl electrodes on the 10-20 system |
| `example_artifacts.csv` | 20 s: chewing 4, 3, 2, 1 times and blinking 4, 3, 2, 1 times |
| `example_alpha.csv` | 40 s, the file PiEEG uses in their own alpha plotting example |

Tasks:
1. Plot `example_artifacts.csv` and find all 10 chewing bursts and all 10 blinks by eye. Then write code that finds them.
2. Run [Mission 1](#mission-1-kill-the-50-hz-hum) on `example_dry.csv`. It has real 50 Hz hum.
3. Which channel in `example_alpha.csv` has the strongest alpha? What does that suggest about where it sat on the head?

Done when your artifact detector finds 10 chews and 10 blinks.

For NWB practice there's far more: [DANDI](https://dandiarchive.org/) hosts thousands of published NWB datasets you can open with `pynwb`, and [OpenNeuro](https://openneuro.org/) has hundreds of human EEG studies.

---

## Mission 1: kill the 50 Hz hum

Every socket in the flat runs at 50 Hz and your body picks it up like an antenna. On the raw signal it can be bigger than the brain waves.

```bash
python record.py --seconds 60 --label hum_test
python mission_1_notch.py recordings/<file>_hum_test.csv
```

Fill in `remove_mains()` in [`code/mission_1_notch.py`](../code/mission_1_notch.py). Done when both checks print **PASS**: hum reduced by more than 95 %, alpha changed by less than 10 %.

<details><summary>Hints</summary>

- `scipy.signal.iirnotch` plus `filtfilt`
- What's the Nyquist frequency at 250 Hz, and what happens to the 100 Hz harmonic?
- Bonus: compare the notch with a plain 40 Hz low-pass. When would you pick which?
</details>

---

## Mission 2: find your alpha peak

Your individual alpha frequency (IAF) is a personal number, usually somewhere between 8 and 12 Hz.

```bash
python record.py --seconds 60 --label eyes_open
python record.py --seconds 60 --label eyes_closed
python spectrum.py recordings/*eyes_open.csv recordings/*eyes_closed.csv
```

Done when you know your peak to 0.5 Hz and the eyes closed power is clearly higher than eyes open.

Bonus: blocks of 30 s open / 30 s closed in one recording, then a spectrogram (`scipy.signal.spectrogram`) where you can see alpha switch on and off.

---

## Mission 3: make it NWB

[Neurodata Without Borders](https://www.nwb.org/) is the standard format neuroscience labs use to share data. [DANDI](https://dandiarchive.org/) is where those datasets get published. Turning lab data into clean NWB is exactly what [CatalystNeuro](https://catalystneuro.com/) does.

```bash
python mission_3_nwb.py recordings/<file>.csv
nwbinspector nwb/
```

The skeleton in [`code/mission_3_nwb.py`](../code/mission_3_nwb.py) has 6 TODOs, one small step each. Done when `nwbinspector` reports no critical issues.

<details><summary>Hints</summary>

- `record.py` already writes a `.json` sidecar with sample rate, units and electrode positions. Use it.
- `ElectricalSeries` wants volts. The CSV is in microvolts. Look at the `conversion` argument.
- Bonus: write a small `PiEEGInterface` in the style of [NeuroConv](https://github.com/catalystneuro/neuroconv) so any PiEEG CSV converts with one call. That would make a nice GitHub link in an application.
</details>

---

## Mission 4: more channels on bare skin

You have 60 stickers and 10 clip cables, but stickers only hold on skin without hair. That still leaves several real EEG and EOG positions:

| Pin | Sticker on | 10-20 / EOG name | What you'll see |
|---|---|---|---|
| E1 | left forehead | Fp1 | blinks, frontal EEG |
| E2 | right forehead | Fp2 | blinks, compare left vs right |
| E3 | left temple, at the outer corner of the eye | LOC / near F7 | horizontal eye movements |
| E4 | right temple, at the outer corner of the eye | ROC / near F8 | horizontal eye movements, opposite sign |

Tasks:
1. Record 60 s while looking left, centre, right in a fixed rhythm. Plot E3 minus E4: that's horizontal EOG, a simple eye tracker.
2. Build a blink detector on E1 and E2 (threshold plus refractory period). Count blinks per minute.
3. Compare alpha on E1 with eyes closed against E3 and E4. Where is it strongest?

Done when you have 4 channels recording cleanly and an eye movement plot that shows left and right.

Getting alpha from the back of the head (O1, O2) needs electrodes that work through hair. That's a later upgrade: dry comb electrodes and a head strap, following the [PiEEG DIY cap guide](https://pieeg.com/?p=633).

---

## Mission 5: read the datasheet

Each sample arrives as 3 bytes per channel from the ADS1299. PiEEG converts them to µV in software.

1. Read the official conversion in the [PiEEG-8 specification](https://docs.pieeg.com/hardware/devices/pieeg-8/specification/#converting-to-microvolts) and in `_decode_channels` in [PiEEG Server hardware.py](https://github.com/pieeg-club/PiEEG-server/blob/main/pieeg_server/hardware.py).
2. Find the data format and the LSB size in the [ADS1299 datasheet](https://www.ti.com/lit/ds/symlink/ads1299.pdf) (sections on data format and input full scale range).
3. Write down every step: bytes, two's complement, gain, VREF, µV.

Done when you can explain each step and you've checked whether the PiEEG formula (about 0.268 µV per count at gain 1) matches the datasheet exactly. If you find a difference, that's a real finding worth an issue on GitHub.

---

## Ideas after that

- Blink detector that toggles something on the laptop
- Eyes closed alarm: alpha above a threshold for 5 s
- Heart rate (ECG): sticker on the left wrist → E1, right wrist → Ref, a leg or ankle → Bias. One channel, then R peak detection. **Never on anyone with a pacemaker or other implant**
- Stream to [LSL](https://labstreaminglayer.org/) from the dashboard and analyse live in MNE
