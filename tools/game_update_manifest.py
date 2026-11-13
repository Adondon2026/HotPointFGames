#!/usr/bin/env python3
"""Generate the immutable release manifest and built-in Android version metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MAX_BYTES = 4 * 1024 * 1024

def make_manifest(game, version, source, epoch):
    data = Path(game).read_bytes()
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError('game file exceeds import limit')
    compile(data, str(game), 'exec')
    return {'schema': 1, 'version': version, 'source': source, 'sourceEpoch': epoch,
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'minHostVersionCode': 4}

def write_manifest(game, output, version=None):
    root = Path(__file__).resolve().parents[1]
    try:
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        epoch = int(subprocess.check_output(['git', 'show', '-s', '--format=%ct', 'HEAD'], cwd=root, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        if version:
            raise
        source, epoch = 'unknown', 0
    result = make_manifest(game, version or ('内置 ' + source[:7]), source, epoch)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('game', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--version')
    args = p.parse_args()
    print(write_manifest(args.game, args.output, args.version))
