# Safety

The PiEEG board connects your skin directly to the electronics. It has **no electrical isolation**. That's normal for a low cost research board, and safe as long as nothing in the chain touches mains power.

## The rules

1. **Raspberry Pi on the powerbank only** while electrodes are on a person. Never a wall power supply.
2. **Laptop on battery.** Unplug the laptop charger before you stick electrodes on. The laptop talks to the Pi over WiFi only, no cable between them.
3. **No HDMI monitor, no USB keyboard plugged into a wall** while recording. If you want a screen on the Pi, it has to run from the same battery.
4. **Not a medical device.** What you see is for learning and research, never for health decisions.
5. **Skin:** stop if a sticker itches or burns. Don't put stickers on broken or irritated skin.

## Why this matters

A wall power supply or a charging laptop can, if it develops a fault, put mains voltage on its low voltage side. With electrodes on your head, that path would go through you. Batteries can't do that. That's the whole reason for the "battery only" rule, and it also gives you a cleaner signal with less 50 Hz hum.

Official notes: [PiEEG safety page](https://docs.pieeg.com/hardware/devices/pieeg-8/safety/) and [liability notice](https://pieeg.com/liability/).
