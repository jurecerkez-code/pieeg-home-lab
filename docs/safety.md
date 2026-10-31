# Safety

The PiEEG-8 connects your skin directly to the electronics and has **no isolation circuitry**. It's safe as long as nothing in the chain touches mains power. These rules follow the official [PiEEG-8 safety page](https://docs.pieeg.com/hardware/devices/pieeg-8/safety/).

## Rules

1. **Battery only.** The Raspberry Pi and the PiEEG-8 run from the powerbank while electrodes are on a person.
2. **Don't charge the powerbank during a session.** A powerbank that's plugged into the wall while powering the Pi is a mains connection. Charge it before, never during.
3. **No cable to anything on the mains.** No wall charger, no HDMI to a TV or monitor, no USB to a plugged-in computer, and **no Ethernet cable** (the Pi 3 has a network port, leave it empty).
4. **Laptop on battery, WiFi only.** Unplug the MacBook charger before the electrodes go on. The MacBook never gets a cable to the Pi.
5. **Not a medical device.** Learning and research only. No diagnosis, monitoring or treatment of anything.
6. **Implants.** Don't use it on anyone with a pacemaker or other implanted electronic device without a physician's approval.
7. **Skin.** Clean, intact skin only. Stop if a sticker itches or burns.
8. **Bare board.** The PiEEG-8 has no case. Hold it by the edges, touch something metal first to discharge static, keep drinks away.

## Safe and unsafe setups

| Setup | With electrodes on |
|---|---|
| Pi + PiEEG-8 on a charged powerbank, MacBook on battery over WiFi | ✅ Safe |
| Powerbank plugged into the wall while powering the Pi | ❌ Never |
| Pi on its wall power supply | ❌ Never |
| HDMI to a TV or monitor on a wall socket | ❌ Never |
| Ethernet or USB cable to a mains-powered device | ❌ Never |
| MacBook charging while connected over WiFi | ❌ Unplug the charger first |

## Why

A wall power supply, a charging laptop or a charging powerbank can, if it develops a fault, put mains voltage on its low voltage side. With electrodes on the skin that path would go through you. A battery that isn't charging can't do that. As a bonus, battery operation also removes most of the 50 Hz hum.

Official pages: [PiEEG-8 safety](https://docs.pieeg.com/hardware/devices/pieeg-8/safety/) · [liability notice](https://pieeg.com/liability/)
