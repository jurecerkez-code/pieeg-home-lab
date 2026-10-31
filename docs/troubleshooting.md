# Troubleshooting

Start with two checks, they narrow down almost everything:

```bash
ssh <username>@raspberrypi.local "pieeg-server doctor"     # software: SPI, GPIO, service, ports
python self_test.py                                         # hardware: board noise with inputs shorted
```

If `self_test.py` passes (all channels under 5 µV RMS), the board is fine and any noise comes from electrodes, cables or surroundings. Based on the official [PiEEG-8 troubleshooting](https://docs.pieeg.com/hardware/devices/pieeg-8/troubleshooting/) page.

## Power and hardware

| Problem | Fix |
|---|---|
| LED on the PiEEG-8 is off | Powerbank on and charged? Board fully seated on all 40 pins? |
| Lightning bolt, random reboots, `under-voltage` in `journalctl -k` | Not enough current. Raspberry Pi recommends 2.5 A for the Pi 3, PiEEG recommends a 3 A powerbank. Use the short official cable and the strongest port of the powerbank. Charge it, many sag when almost empty |
| Board off by one pin | Unplug power, take it off, re-seat it. Pin 1 of the board on pin 1 of the Pi |
| Thermometer icon or `vcgencmd get_throttled` not `0x0` | Too warm or too little power. A small flat heatsink helps, it must fit under the PiEEG-8 |

## Network

### The dashboard does not open

1. Wait a full 2 minutes after plugging in the powerbank.
2. MacBook and Pi on the **same WiFi network**. The Pi 3 uses 2.4 GHz, the Mac may use 5 GHz on the same router, that's fine.
3. `raspberrypi.local` not resolving, see below.
4. SSH in and check: `systemctl status pieeg-server` and `journalctl -u pieeg-server -n 50`.

### live_view.py, record.py or self_test.py can't connect, but the dashboard works

macOS blocks local network access until you allow it. System Settings → Privacy & Security → **Local Network** → turn on Terminal (and Python if listed). Run the script again.

### raspberrypi.local is not found

Macs resolve `.local` names out of the box, but some routers and guest networks block it. Use the Pi's IP address instead:

- Router page (Vodafone: http://192.168.0.1) → list of connected devices → `raspberrypi`
- Or via a working SSH session: `hostname -I`

Then `http://<ip>:1617` and `python live_view.py --host <ip>`.

## PiEEG Server

| Problem | Fix |
|---|---|
| Dashboard shows 16 channels, or the scripts warn "Server reports 16 channels" | The service isn't in PiEEG-8 mode. See [setup step 4](setup-raspberry-pi.md#4-switch-the-service-to-pieeg-8) |
| Flat line on every channel | Board not seated, or SPI off: `ls /dev/spidev*` must list `spidev0.0`. If not: `sudo raspi-config` → Interface Options → SPI → Enable, reboot |
| `Address already in use` | The service is already running. `sudo systemctl stop pieeg-server` before starting the server by hand |
| `Permission denied` on SPI or GPIO | `sudo usermod -aG spi,gpio $USER`, log out and in again |
| Live log | `journalctl -u pieeg-server -f` |

## Signal

| Problem | Likely cause and fix |
|---|---|
| All channels noisy at once | **Ref or Bias.** Fresh stickers on clean, dry skin behind the ears, clips firmly on the snaps |
| One channel huge or stuck | That electrode has no contact. New sticker, wipe the skin, press it on, the clip must bite the metal snap, not the foam |
| Strong 50 Hz hum | Something is on the mains (charger!). Turn on the **Notch** filter and set it to **50 Hz** (the dashboard defaults to 60) |
| Big slow spikes on channel 1 | Blinks and eye movements. That's EOG, real signal, not a fault |
| Bursts of fast noise | Jaw, face or neck muscles (EMG). Relax the face, don't talk or chew |
| Jumps when you move | Cable motion. Sit still, Pi close to your head, cables hanging free |
| No alpha with eyes closed | Expected to be weak on the forehead, alpha is strongest at the back of the head. Eyes closed at least 10 to 30 s, quiet room, look at the spectrum, not the raw line |
| Channels 2 to 8 look like noise | Normal. Nothing is connected to them |

### Quick noise checklist (from PiEEG)

- [ ] Everything on the battery, nothing on the mains, powerbank not charging
- [ ] MacBook charger unplugged
- [ ] Short cables, hanging free
- [ ] Setup on a wooden or plastic surface, away from the router, phones and chargers
- [ ] Sitting still, feet not on a metal surface

## Pi 3 specifics

- PiEEG's current docs list the Pi 4 and 5 as hosts. Elecrow lists the Pi 3, 4 and 5, and the PiEEG Server installer explicitly detects the Pi 3 and selects `/dev/gpiochip0`. If `self_test.py` passes and blinks show up, the Pi 3 works.
- Python SDK: the `*_Pi4.py` scripts are the right ones for the Pi 3 (both use `RPi.GPIO`).
- 1 GB RAM: run only the server on the Pi, analysis on the Mac.

## Still stuck

[PiEEG-8 troubleshooting](https://docs.pieeg.com/hardware/devices/pieeg-8/troubleshooting/) · [PiEEG Discord](https://discord.gg/5Ps24p47) · [PiEEG-8 issues on GitHub](https://github.com/pieeg-club/PiEEG-8/issues)
