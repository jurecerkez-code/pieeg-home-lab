<div align="center">

# PiEEG Home Lab

**Your own 8-channel EEG on a Raspberry Pi. Stick, clip, plug in, see your brain.**

<img src="docs/images/system.svg" alt="Electrodes on the head, clipped to the PiEEG-8 on a Raspberry Pi, powered by a powerbank, streaming over WiFi to a laptop" width="760">

</div>

Everything in the box is already set up and tested. The first signal takes about 5 minutes. After that, the real fun is yours: filtering, spectra, your own alpha peak, and turning recordings into proper NWB files.

> [!CAUTION]
> **Battery only, always.** While electrodes are on your skin, the Raspberry Pi runs from the **powerbank** and your laptop runs **on battery with the charger unplugged**. Nothing on the setup is connected to a wall socket. The PiEEG board has no electrical isolation. Details in [docs/safety.md](docs/safety.md).

> [!NOTE]
> PiEEG is a research and education tool, **not a medical device**. Nothing it shows is a diagnosis.

---

## What's in the box

| | Part | What it does |
|---|---|---|
| 🟩 | **Raspberry Pi 3 Model B** with prepared MicroSD | Runs PiEEG Server, streams data over WiFi |
| 🟧 | **[PiEEG-8 board](https://www.elecrow.com/pieeg.html)** (ADS1299, 24 bit, 250 Hz) | The EEG amplifier. Sits on the Pi's 40 pin header |
| ⚪ | **[Ag/AgCl adhesive electrodes](https://shop.somnomedics.de/en/Single-adhesive-electrode-Ag-AgCl-foam-2.6-cm-OE/SEN010C)**, 2.6 cm, snap, 60 pcs | Single use stickers. Forehead and behind the ears |
| 🔌 | **[Dupont to alligator clip cables](https://www.berrybase.de/en/10pin-jumper/dupont-kabel-female-krokodilklemme-trennbar-20cm?c=338)**, 10 pcs | Clip onto the sticker snap, plug onto the board pin |
| 🔋 | **Powerbank** + [Micro USB cable](https://www.berrybase.de/search?search=raspberry+pi+micro+usb+kabel) | The only power source while recording |
| 🧽 | Alcohol wipes | Clean skin = clean signal |

Your Raspberry Pi, top and bottom:

<p>
<img src="docs/photos/raspberry-pi-3b-top.jpg" alt="Raspberry Pi 3 Model B, top side with the 40 pin GPIO header on the right" width="300">
<img src="docs/photos/raspberry-pi-3b-bottom.jpg" alt="Raspberry Pi 3 Model B, bottom side with the MicroSD card slot" width="300">
</p>

The 40 pin header (right edge, top photo) is where the PiEEG board goes. The MicroSD sits underneath.

---

## Quick start: first signal in 5 minutes

1. **Board on.** If it isn't already: Pi unplugged, press the PiEEG board straight down onto all 40 pins. It should cover the Pi like a lid.
2. **Stickers on.** Wipe the skin, let it dry. One sticker on the left forehead, one on the bony bump behind each ear.
3. **Clip.** Left forehead → **E1**. Behind left ear → **Ref**. Behind right ear → **Biasout**.
4. **Power.** Plug the powerbank into the Pi. Wait about a minute until it has booted and joined the WiFi.
5. **Look.** On your laptop (charger unplugged) open **http://raspberrypi.local:1617** and click **Connect**.

Now blink. Big spikes. Close your eyes and relax for 20 seconds: a 10 Hz rhythm grows in the spectrum. That's your alpha rhythm. 🧠

Step by step with checks and what "good" looks like: **[docs/first-test.md](docs/first-test.md)**

### Where everything plugs in

<img src="docs/images/wiring.svg" alt="PiEEG-8 electrode header with pins Ref, Biasout, E8 to E1, and which sticker each clip goes to" width="760">

<img src="docs/images/placement.svg" alt="Electrode positions: E1 left forehead, E2 right forehead, Ref and Bias on the bone behind each ear" width="760">

---

## Coding on your laptop

The Pi does the hardware. Your Python runs on the laptop and reads the live stream over WiFi.

```bash
git clone <this repo>
cd pieeg-home-lab/code
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python live_view.py                                     # live traces + spectrum
python record.py --seconds 60 --label eyes_closed       # save to recordings/*.csv
python spectrum.py recordings/*eyes_open.csv recordings/*eyes_closed.csv
```

No hardware nearby? Run the simulator and point everything at `localhost`:

```bash
python simulate.py                 # terminal 1: fake PiEEG with alpha, blinks and 50 Hz hum
python live_view.py --host localhost   # terminal 2
```

| File | What it is |
|---|---|
| [`code/eeg_stream.py`](code/eeg_stream.py) | Small client for the PiEEG Server WebSocket (`ws://raspberrypi.local:1616`) |
| [`code/live_view.py`](code/live_view.py) | Live filtered traces and a running spectrum |
| [`code/record.py`](code/record.py) | Records to CSV plus a JSON sidecar with the metadata |
| [`code/spectrum.py`](code/spectrum.py) | Welch spectrum, alpha peak frequency and power |
| [`code/simulate.py`](code/simulate.py) | Fake server with realistic test signals |
| [`code/mission_1_notch.py`](code/mission_1_notch.py) | Mission 1, with an automatic PASS/FAIL check |
| [`code/mission_3_nwb.py`](code/mission_3_nwb.py) | Mission 3 skeleton: CSV to NWB |

---

## Missions 🎯

| # | Mission | Done when |
|---|---|---|
| 1 | **Kill the 50 Hz hum** | `mission_1_notch.py` prints PASS twice |
| 2 | **Find your alpha peak** | You know your own alpha frequency to 0.5 Hz, eyes open vs closed |
| 3 | **Make it NWB** | Your recording passes `nwbinspector` with no errors |
| 4 | **Go beyond the forehead** | Two more channels, and alpha is clearer than at Fp1 |
| 5 | **Read the datasheet** | You can explain every step from 3 raw bytes to one µV value |

Details, hints and bonus ideas: **[docs/missions.md](docs/missions.md)**

---

## Docs

| | |
|---|---|
| [First test](docs/first-test.md) | The 5 minute start, with checks |
| [Safety](docs/safety.md) | The few rules that matter |
| [Raspberry Pi setup](docs/setup-raspberry-pi.md) | How the MicroSD was prepared, to redo it from scratch |
| [Missions](docs/missions.md) | What to build next |
| [Troubleshooting](docs/troubleshooting.md) | Flat lines, noise, WiFi, Pi 3 specifics |

## Built on

- [PiEEG](https://github.com/pieeg-club/PiEEG) hardware and Python SDK by Ildar Rakhmatulin and contributors
- [PiEEG Server](https://github.com/pieeg-club/PiEEG-server): dashboard, WebSocket stream, recording
- [PiEEG docs](https://docs.pieeg.com/hardware/devices/pieeg-8/)

This repo is an unofficial starter kit and is not affiliated with PiEEG. Code here is MIT licensed.

<div align="center">

Merry Christmas 🎄

</div>
