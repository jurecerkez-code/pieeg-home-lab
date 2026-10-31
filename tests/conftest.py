"""Shared test helpers: a running simulate.py on a free port, and a way to talk to it.

Run all tests from the repository root:

    pip install pytest
    python -m pytest tests
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE))
os.environ.setdefault("MPLBACKEND", "Agg")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def sim():
    """Start simulate.py, yield its port, stop it afterwards."""
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(CODE / "simulate.py"), "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("simulate.py did not start")
    yield port
    proc.terminate()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()


def talk(port: int, *commands) -> dict:
    """Open a short extra connection, send commands, return the welcome message."""
    import websockets

    async def go():
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            welcome = json.loads(await ws.recv())
            for c in commands:
                await ws.send(json.dumps(c))
            await asyncio.sleep(0.2)
            return welcome

    return asyncio.run(go())


def script(name: str, *args, cwd, timeout=90, background=False):
    """Run one of the scripts in code/ like a user would."""
    cmd = [sys.executable, str(CODE / name), *map(str, args)]
    if background:
        return subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def only_recording(folder: Path):
    """The single CSV in folder and its sidecar."""
    csvs = sorted(folder.glob("*.csv"))
    assert len(csvs) == 1, csvs
    return csvs[0], json.loads(csvs[0].with_suffix(".json").read_text())
