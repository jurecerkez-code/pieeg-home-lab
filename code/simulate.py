"""
Fake PiEEG Server for testing without hardware.

Streams synthetic 8-channel EEG at 250 Hz on ws://localhost:1616 in the same
JSON format as the real server:
  - alpha rhythm (10 Hz) that gets stronger every other 10 seconds ("eyes closed")
  - 50 Hz mains hum (the noise you'll fight in Mission 1)
  - a blink spike on the frontal channels every few seconds
  - random background noise

Run:   python simulate.py
Then:  python live_view.py --host localhost
"""

import argparse
import asyncio
import json
import math
import random
import time

import websockets

FS = 250
N_CH = 8


def make_sample(n: int, rng: random.Random):
    t = n / FS
    eyes_closed = int(t // 10) % 2 == 1
    alpha_amp = 25.0 if eyes_closed else 6.0
    blink = 0.0
    phase = t % 4.0
    if not eyes_closed and 1.0 < phase < 1.25:
        blink = 150.0 * math.sin(math.pi * (phase - 1.0) / 0.25)
    out = []
    for ch in range(N_CH):
        wax = 0.65 + 0.35 * math.sin(2 * math.pi * 0.35 * t + ch)  # alpha waxes and wanes
        v = alpha_amp * wax * math.sin(2 * math.pi * 10.0 * t + ch * 0.3)
        v += 12.0 * math.sin(2 * math.pi * 50.0 * t)          # mains hum
        v += 8.0 * math.sin(2 * math.pi * 0.2 * t + ch)        # slow drift
        v += rng.gauss(0, 4.0)
        if ch < 2:
            v += blink                                         # Fp1, Fp2
        out.append(round(v, 2))
    return out


async def listen_for_commands(ws):
    """Answer the noise self-test like PiEEG Server does (see self_test.py)."""
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("cmd") == "noise_test":
            duration = min(max(float(msg.get("duration", 3)), 1), 10)
            await ws.send(json.dumps({"noise_test_status": "running"}))
            await asyncio.sleep(duration + 0.5)
            rms = [round(random.uniform(0.6, 1.6), 2) for _ in range(N_CH)]
            await ws.send(json.dumps({"noise_test_result": {
                "rms": rms, "max_rms": max(rms),
                "verdict": "Device OK. Internal noise within spec. (simulated)",
                "recommendation": "This is the simulator, not real hardware.",
                "duration": duration, "samples_collected": int(duration * FS)}}))


async def handler(ws):
    await ws.send(json.dumps({"status": "connected", "sample_rate": FS,
                              "channels": N_CH, "simulated": True}))
    asyncio.ensure_future(listen_for_commands(ws))
    rng = random.Random(1)
    n = 0
    start = time.monotonic()
    while True:
        target = start + n / FS
        delay = target - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        await ws.send(json.dumps({"t": round(time.time(), 6), "n": n,
                                  "channels": make_sample(n, rng)}))
        n += 1


async def main(port: int, host: str):
    async with websockets.serve(handler, host, port):
        print(f"Simulated PiEEG streaming on ws://localhost:{port}  (Ctrl+C to stop)")
        await asyncio.Future()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=1616)
    p.add_argument("--bind", default="127.0.0.1", help="use 0.0.0.0 to reach it from other devices")
    a = p.parse_args()
    try:
        asyncio.run(main(a.port, a.bind))
    except KeyboardInterrupt:
        pass
