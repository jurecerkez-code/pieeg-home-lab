"""
Hardware self test: is the PiEEG-8 board itself healthy?

Runs PiEEG Server's built in noise test. The server shorts every input inside
the ADS1299 (CHnSET = 0x01, as in the official PiEEG noise check), measures the
remaining noise for a few seconds, then switches back to normal recording.

    python self_test.py                  # Pi on raspberrypi.local
    python self_test.py --host 192.168.0.42

Electrodes can stay on or off, the inputs are disconnected inside the chip.
Expected on a healthy board: every channel well under 5 µV RMS (PiEEG Server's
thresholds: under 5 ok, 5 to 15 marginal, above 15 a hardware problem).
If it passes but your recordings are noisy, the noise comes from electrodes,
cables or surroundings, not from the board. See docs/troubleshooting.md.

Not during a recording: while the test runs, the server sends the shorted input
signal to every client, so a recording running at the same time would get a few
seconds of it without any marker.
"""

import argparse
import asyncio
import json

import websockets


async def run(host: str, port: int, duration: float):
    url = f"ws://{host}:{port}"
    async with websockets.connect(url, max_queue=None) as ws:
        await ws.send(json.dumps({"cmd": "noise_test", "duration": duration}))
        print(f"Running {duration:g} s noise test on {host} ...")
        print("(For these seconds every client, dashboard and record.py included, gets the shorted signal.)")
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=duration + 30)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("noise_test_status") == "busy":
                raise SystemExit("A noise test is already running. Try again in a few seconds.")
            if "noise_test_result" in msg:
                return msg["noise_test_result"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="raspberrypi.local")
    p.add_argument("--port", type=int, default=1616)
    p.add_argument("--seconds", type=float, default=3, help="1 to 10, the server limits it to that range")
    a = p.parse_args()
    try:
        r = asyncio.run(run(a.host, a.port, a.seconds))
    except (OSError, asyncio.TimeoutError) as e:
        raise SystemExit(f"Could not run the test on {a.host}: {e}\nSee docs/troubleshooting.md")

    print()
    for i, v in enumerate(r.get("rms", []), start=1):
        flag = "ok" if v < 5 else ("marginal" if v <= 15 else "HIGH")
        print(f"  ch{i}: {v:6.2f} µV RMS   {flag}")
    print()
    print(r.get("verdict", ""))
    print(r.get("recommendation", ""))


if __name__ == "__main__":
    main()
