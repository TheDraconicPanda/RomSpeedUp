"""Screenshot-based boot oracle. Process liveness alone is never a pass."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time

from PIL import Image, ImageChops, ImageGrab, ImageStat


def boot(rom, reference, output, executable='desmume-cli', seconds=20):
    if seconds < 1 or seconds > 120:
        raise ValueError('Boot timeout must be 1..120 seconds')
    rom = Path(rom).resolve()
    reference = Path(reference).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output directory already exists; require a fresh run')
    output.mkdir(parents=True)
    # Only a ROM copy enters the sandbox; emulator saves/config cannot touch user data.
    with tempfile.TemporaryDirectory(prefix='romspeedup-') as temp:
        local = Path(temp) / 'game.nds'
        local.write_bytes(rom.read_bytes())
        env = dict(os.environ, HOME=temp, XDG_CONFIG_HOME=temp, XDG_DATA_HOME=temp)
        with (output / 'emulator.log').open('w') as log:
            proc = subprocess.Popen([executable, '--disable-sound', str(local)],
                                    cwd=temp, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        raise RuntimeError(f'Emulator exited before capture: {proc.returncode}')
                    time.sleep(min(0.2, max(0, deadline - time.monotonic())))
                if proc.poll() is not None:
                    raise RuntimeError(f'Emulator exited before capture: {proc.returncode}')
                actual = ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).convert('RGB')
                actual.save(output / 'screen.png')
                if max(ImageStat.Stat(actual).stddev) < 8:
                    raise RuntimeError('Blank emulator screen is not a successful boot')
                with Image.open(reference) as ref:
                    expected = ref.convert('RGB')
                if actual.size != expected.size:
                    raise RuntimeError('Reference/display geometry mismatch')
                # Reference must be a manually reviewed, nonblank SoulSilver boot screen.
                if max(ImageStat.Stat(expected).stddev) < 8:
                    raise ValueError('Blank reference is not a boot oracle')
                error = sum(ImageStat.Stat(ImageChops.difference(actual, expected)).mean) / (3 * 255)
                if error > 0.015:
                    raise RuntimeError(f'Boot screenshot mismatch: mean error {error:.5f}')
                return dict(status='passed', oracle='reviewed-reference-screenshot',
                            mean_pixel_error=error, seconds=seconds,
                            rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                            reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest())
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
