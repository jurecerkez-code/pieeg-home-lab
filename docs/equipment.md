# Equipment

Every part in the box, what it is, why it's there, and how it connects.

![Kit overview](images/kit.png)

---

## ① Raspberry Pi 3 Model B

<img src="photos/raspberry-pi-3b-top.jpg" alt="Raspberry Pi 3 Model B, top" width="320"> <img src="photos/raspberry-pi-3b-bottom.jpg" alt="Raspberry Pi 3 Model B, bottom" width="320">

| | |
|---|---|
| Board | Raspberry Pi 3 Model B, V1.2 (2015) |
| CPU / RAM | Broadcom BCM2837, 4 × 1.2 GHz, 1 GB |
| WiFi | 2.4 GHz only |
| Power | 5 V via Micro USB (**PWR IN**), up to 2.5 A |
| Storage | 16 GB MicroSD with Raspberry Pi OS Lite and PiEEG Server |
| Role | Talks to the EEG chip over SPI, runs PiEEG Server, streams data over WiFi |

The 40 pin header on the right edge of the top photo is where the PiEEG-8 sits. Pin 1 is the corner pin closest to the MicroSD side.

---

## ② PiEEG-8 board

<img src="https://raw.githubusercontent.com/pieeg-club/PiEEG-docs/main/public/images/hardware/2026/10/pieeg8_board.jpg" alt="PiEEG-8 board" width="320"> <img src="https://raw.githubusercontent.com/pieeg-club/PiEEG-docs/main/public/images/hardware/2026/10/pieeg8_on_pi.jpg" alt="PiEEG-8 mounted on a Raspberry Pi" width="360">

<sub>Photos: PiEEG, from the [official documentation](https://docs.pieeg.com/hardware/devices/pieeg-8/).</sub>

| | |
|---|---|
| Converter | Texas Instruments **ADS1299**, the same chip as OpenBCI Cyton and many research amplifiers |
| Resolution | 24 bit, simultaneous sampling on all channels |
| Sample rate | 250 samples/s (default) |
| Inputs | 8 channels + Reference + Bias, on a 10 pin 2.54 mm **male** header |
| Gain | Programmable 1, 2, 4, 6, 8, 12, 24 |
| Noise | about 0.4 µV internal (manufacturer figure) |
| Link to Pi | SPI0 (pins 19, 21, 23, 24) + DRDY on GPIO 26 (pin 37) |
| Bought at | [Elecrow](https://www.elecrow.com/pieeg.html) |

**What it does:** your brain produces voltages of a few to a few tens of microvolts at the scalp. The ADS1299 amplifies each electrode against the reference, converts it to a 24 bit number 250 times per second, and tells the Pi "new sample ready" by pulling DRDY low. The Bias output drives your body slightly to cancel noise that appears on all electrodes at once, mainly 50 Hz from the mains.

**Electrode header** (left edge of the board, printed as `1-8 Elec`):

<img src="https://raw.githubusercontent.com/pieeg-club/PiEEG-docs/main/public/images/hardware/2026/10/pieeg8_led.png" alt="PiEEG-8 top view with the electrode header on the left and the power LED" width="420">

<sub>Image: PiEEG. Electrode header on the left, LED that lights up when the board has power.</sub>

From top to bottom: **Ref, Biasout, E8, E7, E6, E5, E4, E3, E2, E1**. Always check against the print on your own board.

**Ref** is the shared reference for all 8 channels (the ADS1299's SRB1 input). **Biasout** drives the body to cancel noise common to all electrodes, such as 50 Hz hum. PiEEG's official setup uses ear clips on the earlobes for these two. This kit uses stickers on the mastoids behind the ears instead.

---

## ③ Electrode stickers (Ag/AgCl, foam, 2.6 cm)

| | |
|---|---|
| Type | Self adhesive, single use, silver / silver chloride sensor |
| Size | 2.6 cm diameter foam, metal snap button in the middle |
| Use | Skin without hair: forehead (Fp1, Fp2), behind the ears (mastoids) |
| Amount | 2 packs × 30 = 60 stickers, about 15 sessions with 4 stickers each |
| Bought at | [Somnomedics, SEN010C](https://shop.somnomedics.de/en/Single-adhesive-electrode-Ag-AgCl-foam-2.6-cm-OE/SEN010C) |

**Why Ag/AgCl:** silver chloride is the standard for biosignal electrodes because it gives a stable, low noise contact with the skin. **Why stickers:** no gel in the hair, and they hold still. **Limit:** they don't work through hair, so channels over the scalp need dry comb electrodes later ([Mission 4](missions.md#mission-4-more-channels-on-bare-skin)).

---

## ④ Dupont to alligator clip cables (20 cm)

| | |
|---|---|
| Ends | Female Dupont (fits the board's male pins) ↔ alligator clip (bites the sticker snap) |
| Length | 20 cm |
| Amount | 10, one for every pin on the electrode header |
| Bought at | [BerryBase, DUPAC20](https://www.berrybase.de/en/10pin-jumper/dupont-kabel-female-krokodilklemme-trennbar-20cm?c=338) |

The 10 wires come as a ribbon you can peel apart. Short wires are good for EEG: less antenna, less hum, fewer motion spikes. The Pi has to sit close to your head (shoulder, shelf, or pillow).

> If your board ever turns out to have a socket instead of pins, you need the male version (BerryBase DUPAD20).

---

## ⑤ Powerbank and Micro USB cable

| | |
|---|---|
| Powerbank | 5 V USB A powerbank. Raspberry Pi recommends **2.5 A** for the Pi 3, PiEEG recommends **3 A**. Check the label of the port you use |
| Cable | Official Raspberry Pi Micro USB cable, 1 m ([BerryBase RPI-MUSB-1](https://www.berrybase.de/search?search=raspberry+pi+micro+usb+kabel)) |
| Why | The board has no electrical isolation. A battery is the only safe power source with electrodes on, and it also gives a cleaner signal |

A 10,000 mAh powerbank runs the Pi for several hours. Charge it **before** a session, never while it powers the Pi with electrodes on ([safety](safety.md)).

---

## ⑥ Alcohol wipes

Wipe each spot before sticking an electrode and let it dry. Removes skin oil, lowers contact impedance, cleaner signal.

---

## Not in the box, but needed

- **MacBook**, on battery while recording, same WiFi as the Pi
- **2.4 GHz WiFi**: the Pi 3 can't see 5 GHz networks

## Official references

| | |
|---|---|
| PiEEG-8 docs | [docs.pieeg.com/hardware/devices/pieeg-8](https://docs.pieeg.com/hardware/devices/pieeg-8/) |
| What's in the box (official) | [required equipment](https://docs.pieeg.com/hardware/devices/pieeg-8/required-equipment/) |
| Electrodes & pinout | [connections](https://docs.pieeg.com/hardware/devices/pieeg-8/connections/) |
| Specification and data frame | [specification](https://docs.pieeg.com/hardware/devices/pieeg-8/specification/) |
| Quick start manual (PDF) | [PiEEG-8 on GitHub](https://github.com/pieeg-club/PiEEG-8/blob/main/Manual.%20Conenction%20and%20start%20-%20PiEEG1.pdf) |
| ADS1299 datasheet | [ti.com/lit/ds/symlink/ads1299.pdf](https://www.ti.com/lit/ds/symlink/ads1299.pdf) |
| Research paper | Rakhmatulin et al., [arXiv:2201.02228](https://arxiv.org/abs/2201.02228) |
