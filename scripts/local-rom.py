#!/usr/bin/env python3
"""Inspect a user-owned local ROM or split it for limited-size secure uploads.

Standard library only. Works with Python 3.11+ on Windows/macOS/Linux.
Never changes the input, downloads anything, or transmits data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from romspeedup.rom import inspect


def run(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom', type=Path)
    p.add_argument('--out', required=True, type=Path, help='New private output directory')
    p.add_argument('--split', action='store_true', help='Also create 16 MiB parts; upload every part plus report')
    args = p.parse_args(argv)
    data = args.rom.read_bytes()
    report = inspect(data)
    if args.out.exists():
        raise ValueError('Output directory exists; refusing overwrite')
    args.out.mkdir(parents=True)
    report['parts'] = []
    if args.split:
        size = 16 * 1024 * 1024
        for i, start in enumerate(range(0, len(data), size)):
            chunk = data[start:start+size]
            name = f'rom.part{i:03d}'
            with (args.out / name).open('xb') as out:
                out.write(chunk)
            report['parts'].append(dict(name=name, size=len(chunk), sha256=hashlib.sha256(chunk).hexdigest()))
    with (args.out / 'rom-report.json').open('x') as out:
        json.dump(report, out, indent=2)
        out.write('\n')
    print('Report written:', args.out / 'rom-report.json')
    print('No data transmitted. Keep ROM parts private and out of Git.')


if __name__ == '__main__':
    try:
        run()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
