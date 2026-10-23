from pathlib import Path
from unittest.mock import Mock

from PIL import Image
import pytest

from romspeedup.emulator import boot
from romspeedup.cli import main
from test_pipeline import fixture_rom, profile, manifest
import json


def screen():
    im = Image.new('RGB', (256, 384), 'white')
    im.paste('blue', (0, 0, 128, 192))
    return im


def setup_fake(tmp_path, monkeypatch, actual=None, exit_code=None):
    # Harness test only: no emulator/game validation is claimed by this fixture.
    rom = tmp_path / 'source.nds'
    rom.write_bytes(b'private test data')
    ref = tmp_path / 'reference.png'
    screen().save(ref)
    process = Mock()
    process.poll.return_value = exit_code
    process.returncode = exit_code
    monkeypatch.setattr('romspeedup.emulator.subprocess.Popen', Mock(return_value=process))
    monkeypatch.setattr('romspeedup.emulator.ImageGrab.grab', lambda **kw: actual or screen())
    monkeypatch.setattr('romspeedup.emulator.time.monotonic', Mock(side_effect=[0, 2]))
    return rom, ref, process


def test_boot_oracle_and_sandbox(tmp_path, monkeypatch):
    rom, ref, process = setup_fake(tmp_path, monkeypatch)
    result = boot(rom, ref, tmp_path / 'run', seconds=1)
    assert result['status'] == 'passed' and result['mean_pixel_error'] == 0
    assert rom.read_bytes() == b'private test data'
    process.terminate.assert_called_once()
    from romspeedup import emulator
    kwargs = emulator.subprocess.Popen.call_args.kwargs
    assert kwargs['env']['HOME'] != str(rom.parent)
    assert not Path(kwargs['cwd']).exists()  # disposable files removed


@pytest.mark.parametrize('actual', [Image.new('RGB', (256,384), 'white'),
                                   Image.new('RGB', (2,2), 'red'),
                                   screen().transpose(Image.Transpose.FLIP_TOP_BOTTOM)])
def test_bad_screen_fails(tmp_path, monkeypatch, actual):
    rom, ref, process = setup_fake(tmp_path, monkeypatch, actual)
    with pytest.raises(RuntimeError):
        boot(rom, ref, tmp_path / 'run', seconds=1)
    process.terminate.assert_called_once()
    assert not (tmp_path / 'run' / 'boot.json').exists()


def test_emulator_early_exit_fails(tmp_path, monkeypatch):
    rom, ref, process = setup_fake(tmp_path, monkeypatch, exit_code=1)
    with pytest.raises(RuntimeError, match='exited'):
        boot(rom, ref, tmp_path / 'run', seconds=1)


def test_cli_boot_patched_identity_gate(tmp_path, monkeypatch):
    source = fixture_rom()
    from romspeedup.patch import apply
    m = manifest(source)
    rom = tmp_path / 'patched.nds'
    rom.write_bytes(apply(source, m))
    p = tmp_path / 'profile.json'
    p.write_text(json.dumps(profile(source)))
    mf = tmp_path / 'manifest.json'
    mf.write_text(json.dumps(m))
    fake = Mock(return_value={'status':'passed'})
    monkeypatch.setattr('romspeedup.emulator.boot', fake)
    out = tmp_path / 'run'
    out.mkdir()
    args = ['boot', str(rom), '--profile', str(p), '--manifest', str(mf),
            '--out', str(out), '--reference', str(tmp_path / 'ref.png')]
    assert main(args) == 0
    fake.assert_called_once()
    m['target_sha256'] = '0'*64
    mf.write_text(json.dumps(m))
    assert main(args) == 1
    assert fake.call_count == 1
