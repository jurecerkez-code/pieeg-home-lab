# Raspberry Pi setup

How the MicroSD in the box was prepared. Follow it to redo the setup from scratch or on a new card. About 45 to 90 minutes, most of it waiting: a Pi 3 is slow at updates and installs.

This follows the official [PiEEG-8 How to Start](https://docs.pieeg.com/hardware/devices/pieeg-8/setup/) guide, adapted for a **Raspberry Pi 3 Model B** used **headless** (no monitor, controlled from the MacBook over WiFi).

| | Official PiEEG guide | This kit |
|---|---|---|
| Raspberry Pi | 4 or 5 | 3 Model B (V1.2, 1 GB, 2.4 GHz WiFi) |
| OS | Raspberry Pi OS 64 bit with desktop | Raspberry Pi OS **Lite** 64 bit (no desktop, leaves RAM for the server) |
| Screen | Battery powered monitor, wired keyboard | None. Dashboard on a battery powered laptop, as in PiEEG's "headless option" |
| PiEEG Server | Newest version, installed with one line | One fixed version (commit `9bf3503`), so it behaves exactly like the version this repo was checked against |
| Electrodes | Cap + 2 ear clips | Stick on Ag/AgCl electrodes on forehead and mastoids |

## 1. Flash the MicroSD

1. On the Mac install **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)** and put the MicroSD into a card reader.
2. Choose device **Raspberry Pi 3**, then **Raspberry Pi OS Lite (64-bit)** (under Raspberry Pi OS (other)), then the MicroSD as storage.
3. In the **customisation** step (Imager asks before writing):
   - Hostname: `raspberrypi`
   - Username and password: your choice, write them down
   - WiFi: home network name and password. The Pi 3 only sees **2.4 GHz**. A router that sends 2.4 and 5 GHz under one name is fine
   - Wireless LAN country: **DE**, time zone Europe/Berlin
   - **Enable SSH** with password authentication
4. Write, wait until Imager says it's done, put the card in the Pi.

Current Raspberry Pi OS applies these settings on the first boot with cloud-init: Imager writes them to the files `user-data` and `network-config` on the card ([Raspberry Pi: cloud-init on Raspberry Pi OS](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)).

## 2. First boot

Power the Pi from the powerbank (no electrodes needed for setup). Wait 2 to 5 minutes, the first boot takes longer. Then in Terminal on the Mac:

```bash
ssh <username>@raspberrypi.local
```

Can't find it? See [troubleshooting](troubleshooting.md#raspberrypilocal-is-not-found).

## 3. Install PiEEG Server, one fixed version

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-dev build-essential
git clone https://github.com/pieeg-club/PiEEG-server.git ~/PiEEG-server
cd ~/PiEEG-server
git checkout -b homelab 9bf350310bb492e1373edfe5b0714857f1fe04e9
bash setup.sh
sudo reboot
```

PiEEG's own one line installer (`curl ... install.sh | bash`) clones the newest version and then runs exactly this `setup.sh`. In the repository the script isn't marked executable, so it runs with `bash setup.sh`. Running `setup.sh` from a checkout of one commit gives the same installation, pinned to version 0.49.0 from 16 September 2026, the code this repo's notes about filters and registers refer to. `python3-dev` and `build-essential` are there in case pip has to compile `spidev`.

What `setup.sh` does: enables SPI, builds a Python environment in `~/PiEEG-server/.venv`, installs the server, and creates the `pieeg-server` service that starts on every boot. It recognises the Pi 3 and sets the right GPIO chip (`/dev/gpiochip0`) by itself. It also adds `core_freq_fixed=1` to `/boot/firmware/config.txt`: the SPI clock is derived from the Pi's core clock, and when that clock scales up and down, ADS1299 frames get corrupted (PiEEG's note in `setup.sh`). The setting needs firmware from September 2024 or newer, which current Raspberry Pi OS has (`setup.sh` warns otherwise). Side effect: the core clock no longer drops when the Pi is idle.

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

## 7. Back up the card

Once everything works, an image of the card saves the whole setup. On the Mac, with the card in the reader:

```bash
diskutil list                             # find the card: external, about 16 GB, e.g. /dev/disk4
diskutil unmountDisk /dev/disk4
sudo dd if=/dev/rdisk4 bs=4m | gzip > ~/pieeg-sd-backup.img.gz
```

Double check the disk number: `dd` only reads here, but the restore writes. To restore, write `pieeg-sd-backup.img.gz` with Raspberry Pi Imager (**Use custom**). The image contains the WiFi password, keep it private.

## Updating PiEEG Server later

On purpose only, it may change behaviour this repo relies on:

```bash
cd ~/PiEEG-server
git checkout main && git pull
bash setup.sh
```

`setup.sh` writes the service file again, so do step 4 once more. To go back: `git checkout homelab && bash setup.sh`, then step 4.

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
- If `RPi.GPIO` fails with an edge detection error on a recent kernel, install the drop in replacement `pip install rpi-lgpio`, the same fix PiEEG gives for the Pi 5.
- `Permission denied` on SPI or GPIO: `sudo usermod -aG spi,gpio $USER`, then log out and in again.

Source: [PiEEG-8 Software](https://docs.pieeg.com/hardware/devices/pieeg-8/software/).
