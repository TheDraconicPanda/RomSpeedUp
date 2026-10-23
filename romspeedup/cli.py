import argparse
import hashlib
import json
from pathlib import Path
import sys

from .rom import inspect, verify
from .patch import apply, bps


def load(path):
    return json.loads(Path(path).read_text())


def exclusive(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local-only, verified USA SoulSilver tooling')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'verify', 'build', 'disasm', 'boot'):
        p = sub.add_parser(name)
        p.add_argument('rom', type=Path)
        if name != 'inspect':
            p.add_argument('--profile', type=Path, default=Path('profiles/soulsilver-usa.json'))
        if name == 'build':
            p.add_argument('manifest', type=Path)
            p.add_argument('--out', required=True, type=Path, help='New output directory')
        if name == 'disasm':
            p.add_argument('--offset', type=lambda x: int(x, 0), default=0,
                           help='Offset within decompressed ARM9, not ROM offset')
            p.add_argument('--length', type=lambda x: int(x, 0), default=256)
            p.add_argument('--thumb', action='store_true')
        if name == 'boot':
            p.add_argument('--reference', required=True, type=Path)
            p.add_argument('--out', required=True, type=Path)
            p.add_argument('--emulator', default='desmume-cli')
            p.add_argument('--manifest', type=Path, help='Verified manifest for patched ROM boot')
            p.add_argument('--seconds', type=int, default=20)
    args = parser.parse_args(argv)
    try:
        source = args.rom.read_bytes()
        if args.command == 'boot' and args.manifest:
            manifest = load(args.manifest)
            report = inspect(source)
            expected = load(args.profile)
            if manifest.get('status') != 'verified' or manifest.get('schema') != 1:
                raise ValueError('Boot requires a verified schema-1 target manifest')
            if report['sha256'] != manifest['target_sha256']:
                raise ValueError('Patched ROM does not match target manifest')
            for key in ('game_code', 'revision', 'size'):
                if report[key] != expected[key]:
                    raise ValueError('Patched ROM profile mismatch')
        else:
            report = inspect(source) if args.command == 'inspect' else verify(source, load(args.profile))
        if args.command == 'build':
            manifest = load(args.manifest)
            target = apply(source, manifest)
            inspect(target)
            if args.out.exists():
                raise ValueError('Output directory exists; refuse overwrite')
            args.out.mkdir(parents=True)
            exclusive(args.out / 'patched.nds', target)
            exclusive(args.out / 'patch.bps', bps(source, target))
            report = dict(source=report, target=inspect(target), manifest_sha256=
                          hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                          features=manifest['features'], status='built-not-emulator-verified')
            exclusive(args.out / 'build.json', (json.dumps(report, indent=2) + '\n').encode())
        elif args.command == 'disasm':
            import capstone
            import ndspy.rom
            import ndspy.codeCompression
            rom = ndspy.rom.NintendoDSRom(source)
            code = ndspy.codeCompression.decompress(rom.arm9)
            if args.offset < 0 or args.length <= 0 or args.offset + args.length > len(code):
                raise ValueError('Requested disassembly outside decompressed ARM9')
            engine = capstone.Cs(capstone.CS_ARCH_ARM,
                                 capstone.CS_MODE_THUMB if args.thumb else capstone.CS_MODE_ARM)
            instructions = [dict(address=i.address, bytes=i.bytes.hex(), mnemonic=i.mnemonic,
                                 operands=i.op_str) for i in engine.disasm(
                                     code[args.offset:args.offset+args.length], rom.arm9RamAddress + args.offset)]
            if not instructions:
                raise ValueError('No instructions decoded; check mode and offset')
            report = dict(arm9_ram=rom.arm9RamAddress, decompressed_size=len(code),
                          warning='Decoded instructions do not prove code boundaries or patch safety',
                          instructions=instructions)
        elif args.command == 'boot':
            from .emulator import boot
            report = boot(args.rom, args.reference, args.out, args.emulator, args.seconds)
            exclusive(args.out / 'boot.json', (json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
