#!/usr/bin/env python3
"""Read-only check of the detached source oracle, not runtime/asset attestation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


class PinError(ValueError):
    pass


def git(source, *args):
    result = subprocess.run(['git', '-C', str(source), *args], text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise PinError(result.stderr.strip() or 'git command failed')
    return result.stdout.strip()


def verify(source, lock):
    source = Path(source).resolve()
    commit = lock.get('commit', '')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise PinError('Lock requires an exact 40-hex upstream commit')
    actual = git(source, 'rev-parse', 'HEAD')
    if actual != commit:
        raise PinError(f'Wrong oracle HEAD: expected {commit}, observed {actual}')
    dirty = git(source, 'status', '--porcelain', '--untracked-files=no')
    if dirty:
        raise PinError('Oracle has tracked changes; use a clean pinned checkout')
    hashes = lock.get('source_hashes')
    if not isinstance(hashes, dict) or not hashes:
        raise PinError('No critical source hashes: cannot verify an empty lock')
    verified = []
    for relative, expected in hashes.items():
        p = PurePosixPath(relative)
        if p.is_absolute() or '..' in p.parts or '\\' in relative:
            raise PinError(f'Unsafe lock path: {relative}')
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise PinError(f'Invalid SHA-256 for {relative}')
        file = (source / relative).resolve()
        if not file.is_relative_to(source) or not file.is_file():
            raise PinError(f'Missing critical source file (possibly sparse): {relative}')
        observed = hashlib.sha256(file.read_bytes()).hexdigest()
        if observed != expected:
            raise PinError(f'Source checksum mismatch: {relative}')
        verified.append(relative)
    return {'status': 'static_source_verified', 'commit': actual,
            'checked_source_files': verified, 'runtime_verified': False,
            'model_assets_verified': False,
            'note': 'This check does not build, load models, run GROBID, or prove parity.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--lock', type=Path, default=Path(__file__).resolve().parents[1] / 'contracts/upstream-lock.json')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.source, json.loads(args.lock.read_text()))
        raw = json.dumps(result, indent=2) + '\n'
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open('x') as stream:
                stream.write(raw)
        print(raw, end='')
        return 0
    except (PinError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
