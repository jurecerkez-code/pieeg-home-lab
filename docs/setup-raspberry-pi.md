# Raspberry Pi setup

This is how the MicroSD in the box was prepared. Follow it to redo the setup from scratch, or on a new card. About 30 minutes, most of it waiting.

Hardware: **Raspberry Pi 3 Model B** (V1.2, 1 GB RAM, 2.4 GHz WiFi only), PiEEG-8, MicroSD of 16 GB or more.

## 1. Flash the MicroSD

1. On the laptop install **[Raspberry Pi Imager](https://www.raspberrypi.com/software/)**.
2. Device: **Raspberry Pi 3**. OS: **Raspberry Pi OS Lite (64-bit)** under *Raspberry Pi OS (other)*. Lite has no desktop, which leaves more of the 1 GB RAM for the server. You use everything from the laptop anyway.
3. Storage: the MicroSD. Click **Next**, then **Edit settings**:
   - Hostname: `raspberrypi`
   - Username and password: your choice, write them down
   - WiFi: the home network name and password (must have a **2.4 GHz** band, the Pi 3 can't see 5 GHz)
   - Country: DE
   - Services tab: **Enable SSH**, password authentication
4. Write, wait, put the card in the Pi.

## 2. First boot

Power the Pi from the powerbank (no electrodes needed for setup). Wait 2 minutes, then on the laptop:

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

The installer enables SPI, installs the server into `~/PiEEG-server`, and creates a service that starts on boot. It detects the Pi 3 and picks the right GPIO chip by itself.

## 4. Switch the service to 8 channels

The service starts in 16 channel mode by default. PiEEG-8 has one ADS1299, so add `--device pieeg8`:

```bash
ssh <username>@raspberrypi.local
grep ExecStart /etc/systemd/system/pieeg-server.service       # look first
sudo sed -i '/^ExecStart=/ s/$/ --device pieeg8/' /etc/systemd/system/pieeg-server.service
grep ExecStart /etc/systemd/system/pieeg-server.service       # now ends with --device pieeg8
sudo systemctl daemon-reload
sudo systemctl restart pieeg-server
```

Official instructions for this step: [PiEEG-8 How to Start](https://docs.pieeg.com/hardware/devices/pieeg-8/setup/).

## 5. Check

```bash
pieeg-server doctor                     # checks Pi model, SPI, GPIO, ports, service
systemctl status pieeg-server           # should say active (running)
journalctl -u pieeg-server -n 30        # last log lines
```

Then open **http://raspberrypi.local:1617** on the laptop and click **Connect**.

## 6. Test on yourself

Do the [first test](first-test.md) once with your own forehead. Blink, see spikes. If that works, everything works.

## Optional: the official Python SDK

The board's original Python scripts talk to the ADS1299 directly, without the server. Useful for learning the registers. Stop the server first, they can't share the SPI bus.

```bash
sudo systemctl stop pieeg-server
git clone https://github.com/pieeg-club/PiEEG.git
python3 -m venv --system-site-packages ~/pieeg-env && source ~/pieeg-env/bin/activate
pip install spidev matplotlib scipy pandas openpyxl RPi.GPIO
cd PiEEG/1.GUI && python save_data_short_Pi4.py      # the "Pi4" scripts are the ones for Pi 3 too
sudo systemctl start pieeg-server                     # when done
```

The live graph scripts need a screen on the Pi, so on a headless Pi use the `save_data` ones.
