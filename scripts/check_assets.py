"""Reject accidentally tracked copyrighted/private binary artifacts."""
from pathlib import Path
import subprocess
import sys

files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
forbidden = {'.nds', '.srl', '.gba', '.sav', '.dsv', '.dst', '.bin', '.bios'}
bad = [p for p in files if p and (Path(p).suffix.lower() in forbidden or
                                 p.split('/')[0] in {'private', 'build', 'artifacts'})]
if bad:
    print('Refusing tracked private/generated assets:', *bad, sep='\n')
    sys.exit(1)
print('Tracked artifact check passed')
