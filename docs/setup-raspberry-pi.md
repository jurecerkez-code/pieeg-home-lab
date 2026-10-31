# Raspberry Pi setup

How the MicroSD in the box was prepared. Follow it to redo the setup from scratch or on a new card. About 30 minutes, most of it waiting.

This follows the official [PiEEG-8 How to Start](https://docs.pieeg.com/hardware/devices/pieeg-8/setup/) guide, adapted for a **Raspberry Pi 3 Model B** used **headless** (no monitor, controlled from the MacBook over WiFi).

| | Official PiEEG guide | This kit |
|---|---|---|
| Raspberry Pi | 4 or 5 | 3 Model B (V1.2, 1 GB, 2.4 GHz WiFi) |
| OS | Raspberry Pi OS 64-bit with desktop | Raspberry Pi OS **Lite** 64-bit (no desktop, leaves RAM for the server) |
| Screen | Battery-powered monitor, wired keyboard | None. Dashboard on a battery-powered laptop, as in PiEEG's "headless option" |
| Electrodes | Cap + 2 ear clips | Stick-on Ag/AgCl electrodes on forehead and mastoids |

## 1. Flash the MicroSD

1. On the Mac install **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)** and put the MicroSD into a card reader.
2. Choose device **Raspberry Pi 3**, then OS **Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)**, then the MicroSD as storage.
3. In the **customisation** step (Imager asks before writing):
   - Hostname: `raspberrypi`
   - Username and password: your choice, write them down
   - WiFi: home network name and password. The Pi 3 only sees **2.4 GHz**. A router that sends 2.4 and 5 GHz under one name is fine
   - Wireless LAN country: **DE**, time zone Europe/Berlin
   - **Enable SSH** with password authentication
4. Write, wait until Imager says it's done, put the card in the Pi.

## 2. First boot

Power the Pi from the powerbank (no electrodes needed for setup). Wait 2 minutes, then in Terminal on the Mac:

```bash
ssh <username>@raspberrypi.local
```

Can't find it? See [troubleshooting](troubleshooting.md#raspberrypilocal-is-not-found).

## 3. Install PiEEG Server

```bash
sudo apt update && sudo apt full-upgrade -y
curl -sSL https://raw.githubusercontent.com/pieeg-club/PiEEG-server/main/install.sh | bash
sudo reboot
```

The installer enables SPI, installs the server into `~/PiEEG-server`, and creates a service that starts on every boot. It recognises the Pi 3 and sets the right GPIO chip (`/dev/gpiochip0`) by itself.

## 4. Switch the service to PiEEG-8

The service starts in **16 channel mode** by default. The PiEEG-8 has one ADS1299, so add `--device pieeg8`. This is the official command, run it **once**:

```bash
ssh <username>@raspberrypi.local
sudo sed -i 's|bin/pieeg-server|bin/pieeg-server --device pieeg8|' /etc/systemd/system/pieeg-server.service
grep ExecStart /etc/systemd/system/pieeg-server.service      # must contain --device pieeg8 exactly once
sudo systemctl daemon-reload
sudo systemctl restart pieeg-server
```

If you ran it twice and see `--device pieeg8` twice, edit the line by hand: `sudo nano /etc/systemd/system/pieeg-server.service`.

## 5. Check

```bash
pieeg-server doctor                     # checks Pi model, SPI, GPIO, ports, service
systemctl status pieeg-server           # should say active (running)
journalctl -u pieeg-server -n 30        # last log lines
```

Then, with the PiEEG-8 mounted, from the Mac:

```bash
cd pieeg-home-lab/code && source .venv/bin/activate
python self_test.py                     # board noise test, every channel should be under 5 µV RMS
```

Open **http://raspberrypi.local:1617** on the Mac and click **Connect**. The dashboard must show **8** channels. Sixteen means step 4 didn't apply.

## 6. Test on yourself

Do the [first test](first-test.md) once with your own forehead. Blink, see spikes. If that works, everything works.

## Optional: the official Python SDK

PiEEG's original scripts talk to the ADS1299 directly, without the server. Good for learning the registers. Stop the server first, both can't use the SPI bus at the same time.

```bash
sudo systemctl stop pieeg-server
sudo apt install -y python3-venv python3-dev git
python3 -m venv --system-site-packages ~/pieeg-env
source ~/pieeg-env/bin/activate
pip install spidev matplotlib scipy pandas openpyxl RPi.GPIO
git clone https://github.com/pieeg-club/PiEEG-8.git
cd PiEEG-8/1.GUI
python save_data_short_Pi4.py           # the Pi 4 scripts are the right ones for a Pi 3
sudo systemctl start pieeg-server       # when done
```

- The script saves to Excel after 10,000 samples (40 s at 250 Hz). Change that number in the script for longer recordings.
- The live graph scripts (`1.8_ch_Pi4.py`) open a window, so they need a screen on the Pi. Headless, use the `save_data` scripts.
- If `RPi.GPIO` fails with an edge detection error on a recent kernel, install the drop-in replacement `pip install rpi-lgpio`, the same fix PiEEG gives for the Pi 5.
- `Permission denied` on SPI or GPIO: `sudo usermod -aG spi,gpio $USER`, then log out and in again.

Source: [PiEEG-8 Software](https://docs.pieeg.com/hardware/devices/pieeg-8/software/).
