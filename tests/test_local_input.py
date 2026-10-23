import hashlib
import json
from pathlib import Path
import subprocess
import sys

from test_pipeline import fixture_rom


def test_local_report_and_split(tmp_path):
    source = fixture_rom() + b'\xff' * (16 * 1024 * 1024)
    rom = tmp_path / 'source.nds'
    rom.write_bytes(source)
    out = tmp_path / 'parts'
    result = subprocess.run([sys.executable, 'scripts/local-rom.py', str(rom),
                             '--out', str(out), '--split'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads((out / 'rom-report.json').read_text())
    assert report['sha256'] == hashlib.sha256(source).hexdigest()
    assert len(report['parts']) == 2
    combined = bytearray()
    for part in report['parts']:
        content = (out / part['name']).read_bytes()
        assert len(content) <= 16 * 1024 * 1024
        assert hashlib.sha256(content).hexdigest() == part['sha256']
        combined += content
    assert combined == source and rom.read_bytes() == source
    again = subprocess.run([sys.executable, 'scripts/local-rom.py', str(rom),
                            '--out', str(out)], capture_output=True, text=True)
    assert again.returncode != 0
