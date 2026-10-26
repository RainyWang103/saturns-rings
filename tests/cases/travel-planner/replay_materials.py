#!/usr/bin/env python3
"""Read-only materials gateway for isolated offline replays, with local telemetry.

Session config contains variant_root and input paths. start/read/finish record
wall clock, material bytes and output digest; this does not invoke a model or
measure model reasoning, tokens, real search latency or a ChatGPT app workflow.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('action', choices=('start', 'read', 'finish'))
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()
    session = args.session.resolve()
    config = json.loads((session / 'config.json').read_text())
    root = Path(config['variant_root']).resolve()
    log = session / 'events.jsonl'
    def record(event):
        event.update(monotonic=time.monotonic(), utc=time.time())
        with log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
    if args.action == 'start':
        if log.exists():
            parser.error('session already started')
        record({'action': 'start'})
        print('Session started. Read input via read @input; skill paths are relative to variant_root.')
    elif args.action == 'read':
        if not log.exists() or not args.paths:
            parser.error('start the session and specify material paths')
        for name in args.paths:
            path = Path(config['input']).resolve() if name == '@input' else (root / name).resolve()
            if name != '@input' and not path.is_relative_to(root):
                parser.error('material path escapes variant root')
            data = path.read_bytes()
            record({'action': 'read', 'material': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
            print(f'--- {name} ---\n{data.decode("utf-8")}')
    else:
        if len(args.paths) != 1 or not log.exists():
            parser.error('finish requires one output file after start')
        path = (session / args.paths[0]).resolve()
        if not path.is_relative_to(session):
            parser.error('output must be in the session directory')
        data = path.read_bytes()
        record({'action': 'finish', 'output': path.name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
        print('Recorded output digest; this is not a quality verdict.')


if __name__ == '__main__':
    main()
