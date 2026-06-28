#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from sc4s_manager.packs import load_packs, validate_pack_fixtures

def main() -> int:
    packs = load_packs(ROOT / 'packs')
    total = 0
    for pack in packs:
        results = validate_pack_fixtures(pack, pack['pack_dir'])
        total += len(results)
        for result in results:
            print(f"{pack['id']}:{result['id']} events={result['event_count']} families={result['families']} markers={result['markers']}")
    print(f'validated {total} fixture set(s)')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
