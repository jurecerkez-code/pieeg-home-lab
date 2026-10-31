# Missions

Each mission is small enough for one evening. Do them in order or not, they're yours.

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

## Mission 4: go beyond the forehead

Alpha is strongest over the back of the head (O1, O2), where there's hair. Options, cheapest first:

1. Put a sticker as low on the back of the neck as possible, just under the hairline, on **E2**. Compare alpha with E1.
2. Part the hair carefully at O1 and press a sticker to the scalp. Does it hold?
3. Order dry comb Ag/AgCl electrodes and build a head strap following the [PiEEG DIY cap guide](https://pieeg.com/?p=633).

Done when you have 3 channels and alpha is clearer than at Fp1.

---

## Mission 5: read the datasheet

Each sample arrives as 3 bytes per channel from the ADS1299. PiEEG converts them to µV in software.

1. Find the conversion in the official code: `_decode_channels` in [PiEEG Server `hardware.py`](https://github.com/pieeg-club/PiEEG-server/blob/main/pieeg_server/hardware.py).
2. Find the data format and LSB size in the [ADS1299 datasheet](https://www.ti.com/lit/ds/symlink/ads1299.pdf) (look for the section on data format and the input full scale range).
3. Write down every step: bytes, two's complement, gain, VREF, µV.

Done when you can explain each step and you've checked whether the code's formula matches the datasheet exactly. If you find a difference, that's a real finding worth an issue on GitHub.

---

## Ideas after that

- Blink detector that toggles something on the laptop
- Eyes closed alarm: alpha above a threshold for 5 s
- Heart rate: an electrode on each wrist, one channel, R peak detection (that's ECG, the board does that too)
- Stream to [LSL](https://labstreaminglayer.org/) from the dashboard and analyse live in MNE
