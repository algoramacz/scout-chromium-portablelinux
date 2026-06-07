#!/usr/bin/env python3
# Copyright 2026 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license.
#
# Codegen for the Scout fingerprint combination tables.
#
# Each <name>.json in this directory holds ONE seed-spoof value table as a list
# of row-objects. This script emits the matching <name>.inc: the C++ aggregate
# initializer ROWS only (the surrounding `struct` + `constexpr T kTable[] = {`
# ... `};` stay in the consuming .cc file, which #includes the .inc). So updating
# a table -- e.g. adding a freshly-released Chrome version to chrome_versions.json
# -- is a plain JSON edit; the next build regenerates the .inc and recompiles.
#
# Value encoding (key order in each JSON object MUST match the C++ struct fields):
#   number   -> emitted bare           (1920, 0.5)
#   true/false -> emitted bare         (true, false)
#   "string" -> emitted as a quoted, escaped C string literal
#   "@token" -> emitted BARE with the leading @ stripped (for enums / constants,
#               e.g. "@GpuVendor::kNvidia" -> GpuVendor::kNvidia)
#   keys beginning with "_" are NOT values: "_comment" becomes a trailing // note;
#   any other "_*" key is ignored (room for editor metadata).
#
# Usage:
#   generate.py            # regenerate every <name>.inc from <name>.json (in-place,
#                          # write-if-changed so unchanged tables don't force rebuilds)
#   generate.py --check    # exit non-zero if any .inc is stale vs its .json (CI guard)

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTOGEN = ('// AUTO-GENERATED from {src} by generate.py -- DO NOT EDIT.\n'
           '// Edit the .json and rebuild (the build regenerates this .inc).\n')


def _c_string(value):
    out = ['"']
    for ch in value:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _encode(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, float) else str(value)
    if isinstance(value, str):
        if value.startswith('@'):
            return value[1:]
        return _c_string(value)
    raise ValueError(f'unsupported JSON value type: {type(value).__name__} ({value!r})')


def render(json_path):
    rows = json.loads(json_path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f'{json_path.name}: top level must be a JSON array of row objects')
    lines = [AUTOGEN.format(src=json_path.name)]
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f'{json_path.name}: each row must be an object, got {row!r}')
        values = [_encode(v) for k, v in row.items() if not k.startswith('_')]
        line = '    {' + ', '.join(values) + '},'
        if isinstance(row.get('_comment'), str):
            line += '  // ' + row['_comment']
        lines.append(line)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true',
                        help='verify every .inc is up to date; do not write')
    parser.add_argument('--dir', type=Path, default=HERE,
                        help='directory containing the .json tables (default: alongside this script)')
    args = parser.parse_args()

    stale = []
    for json_path in sorted(args.dir.glob('*.json')):
        inc_path = json_path.with_suffix('.inc')
        rendered = render(json_path)
        current = inc_path.read_text() if inc_path.exists() else None
        if current == rendered:
            continue
        if args.check:
            stale.append(inc_path.name)
            continue
        inc_path.write_text(rendered)
        print(f'generated {inc_path.name} from {json_path.name}')

    if args.check and stale:
        print('STALE (run generate.py): ' + ', '.join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
