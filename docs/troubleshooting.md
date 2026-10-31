# Troubleshooting

## The dashboard does not open

1. Wait a full 2 minutes after plugging in the powerbank.
2. Laptop and Pi on the **same WiFi**. The Pi 3 only sees **2.4 GHz** networks.
3. `raspberrypi.local` not resolving, see below.
4. SSH in and check the server: `systemctl status pieeg-server` and `journalctl -u pieeg-server -n 50`.

## live_view.py or record.py can't connect, but the dashboard works

macOS blocks local network access until you allow it. System Settings → Privacy & Security → **Local Network** → turn on Terminal (and Python if listed). Then run the script again.

## raspberrypi.local is not found

Macs resolve `.local` names out of the box, but some routers and guest networks block it. Find the Pi's IP address instead:

- Router admin page, list of connected devices, look for `raspberrypi`
- Or on the Pi (with a screen, or via a working SSH session): `hostname -I`

Then use `http://<ip>:1617` and `python live_view.py --host <ip>`.

## Lightning bolt icon, random reboots, "under-voltage" in the logs

The Pi 3 needs a steady 5 V at up to 2.5 A. Check `journalctl -k | grep -i voltage`.

- Use the short official Micro USB cable, not a long thin one
- Use the powerbank port marked 2.4 A or higher
- Charge the powerbank, many drop voltage when almost empty

## Flat line on every channel, or "no data"

- Board not fully seated on the 40 pins. Unplug power, press it down evenly.
- Service running in the wrong mode. `grep ExecStart /etc/systemd/system/pieeg-server.service` must end with `--device pieeg8`. See [setup step 4](setup-raspberry-pi.md#4-switch-the-service-to-8-channels).
- SPI off: `ls /dev/spidev*` must list `spidev0.0`. If not: `sudo raspi-config` → Interface Options → SPI → Yes, then reboot.
- Run `pieeg-server doctor` and read what it flags.

## One channel huge, or stuck at a large value

That electrode isn't making contact. Fresh sticker, wipe the skin, press it on, check the clip bites the snap and not the plastic.

## Lots of 50 Hz hum

- Turn on the 50 Hz notch filter in the dashboard (not 60)
- Laptop charger unplugged? (Required anyway, see [safety](safety.md))
- Ref and Bias stickers on bare skin, fresh, pressed on
- Move away from power strips, lamps, monitors
- Let the cables hang free, don't coil them, don't touch them while recording

## Spikes every time you move

Cable motion. Sit still, rest the Pi on the table close to you, let the 20 cm cables hang without pulling. Mission material: detect and remove these artifacts.

## No alpha with eyes closed

Normal at first on the forehead, alpha is strongest at the back of the head. Relax fully, eyes closed for 30 s, jaw loose. Look at the spectrum, not the raw trace. Then try [Mission 4](missions.md#mission-4-go-beyond-the-forehead).

## Pi 3 specifics

- PiEEG's own README lists Raspberry Pi 4 and 5 as hosts. Elecrow lists Pi 3, 4 and 5, and PiEEG Server's installer explicitly detects the Pi 3. If the [first test](first-test.md) works, the Pi 3 is fine.
- In the official Python SDK, the `*_Pi4.py` scripts are the right ones for the Pi 3 (both use `RPi.GPIO`).
- 1 GB RAM: run only the server on the Pi, do analysis on the laptop.
- Getting warm is fine. If you see a thermometer icon or `vcgencmd get_throttled` isn't `0x0`, a small flat heatsink on the processor helps. It must be low enough to fit under the PiEEG board.

## Still stuck

- [PiEEG troubleshooting](https://docs.pieeg.com/hardware/devices/pieeg-8/troubleshooting/)
- [PiEEG Discord](https://discord.gg/5Ps24p47)
