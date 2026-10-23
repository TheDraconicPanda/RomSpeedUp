#!/usr/bin/env python3
"""Capture identical fresh-boot frame sequences in separate processes.

Use `--capture` twice (one ROM per process), review baseline.png manually, then
`--compare` both images. A matching image is a boot smoke check, not gameplay or
audio approval. Use the same py-desmume version/display backend for both captures.
"""
import argparse
import os
from pathlib import Path
import shutil
import tempfile

from PIL import Image,ImageChops,ImageStat

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--capture',type=Path)
p.add_argument('--out',type=Path)
p.add_argument('--compare',nargs=2,type=Path)
a=p.parse_args()
if a.compare:
    with Image.open(a.compare[0]) as b,Image.open(a.compare[1]) as c:
        if b.size!=c.size:raise SystemExit('Geometry mismatch')
        if min(max(ImageStat.Stat(im.convert('RGB')).stddev) for im in (b,c))<8:
            raise SystemExit('Blank capture is not boot evidence')
        error=sum(ImageStat.Stat(ImageChops.difference(b.convert('RGB'),c.convert('RGB'))).mean)/(3*255)
        print('Normalized mean pixel error:',error)
        if error>0.015:raise SystemExit('Boot capture mismatch')
        print('Matched reviewed baseline capture; gameplay/audio remain unverified')
elif a.capture and a.out:
    from desmume.emulator import DeSmuME
    rom,out=a.capture.resolve(),a.out.resolve()
    if out.exists():raise SystemExit('Fresh capture output required')
    old=Path.cwd()
    with tempfile.TemporaryDirectory(prefix='v4-boot-',dir='/workspace') as tmp:
        tmp=Path(tmp);shutil.copyfile(rom,tmp/'game.nds')
        os.environ.update(HOME=str(tmp),XDG_CONFIG_HOME=str(tmp),XDG_DATA_HOME=str(tmp))
        (tmp/'.config/desmume').mkdir(parents=True)
        os.chdir(tmp);e=DeSmuME()
        try:
            e.open(str(tmp/'game.nds'))
            for i in range(600):e.cycle(with_joystick=False)
            e.input.keypad_update(8)  # START
            for i in range(2):e.cycle(with_joystick=False)
            e.input.keypad_update(0)
            for i in range(120):e.cycle(with_joystick=False)
            out.parent.mkdir(parents=True,exist_ok=True);e.screenshot().save(out)
        finally:e.destroy();os.chdir(old)
else:p.error('Use --capture ROM --out IMAGE or --compare BASELINE CANDIDATE')
