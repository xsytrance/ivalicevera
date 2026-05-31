#!/usr/bin/env python3
"""
FFT Battle Overlay HP/MP Mapper
Compares autosaves from the same battle to find current HP/MP fields.
Usage: python fft_overlay_mapper.py <autosave_before> <autosave_after> [autosave_mp]
"""
import struct
import sys
from pathlib import Path

def find_markers(data, marker_id=b'\x00\x21', region_start=0, region_end=None):
    """Find all battle overlay markers (0021 prefix)."""
    if region_end is None:
        region_end = len(data)
    
    positions = []
    for i in range(region_start, region_end - 140):
        if data[i:i+2] == marker_id and data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11':
            tail = data[i+9:i+12]
            if tail in [b'\x01\x01\x00', b'\x10\x11\x00']:
                name_start = i + 12 + 92
                name_end = data.find(b'\x00', name_start, name_start + 30)
                name = data[name_start:name_end].decode('ascii', errors='replace') if name_end > name_start else ''
                stats = [struct.unpack_from('<H', data, i + 12 + j*2)[0] for j in range(46)]
                positions.append({
                    'offset': i,
                    'marker_id': marker_id,
                    'tail': tail.hex(),
                    'name': name,
                    'stats': stats,
                })
    return positions

def load_paths():
    if len(sys.argv) >= 3:
        return [Path(p) for p in sys.argv[1:]]
    base = Path('/home/xsyvps/fft-battle-saves')
    return [
        base / 'undamaged' / 'autoenhanced' / 'resume_en00_attack.sav',
        base / 'damaged' / 'autoenhanced' / 'resume_en00_attack.sav',
    ]

paths = load_paths()
for p in paths:
    if not p.exists():
        print(f"ERROR: {p} not found")
        print("Usage: python fft_overlay_mapper.py <before_autosave.sav> <after_autosave.sav>")
        sys.exit(1)

datas = [p.read_bytes() for p in paths]

print(f"Battle Overlay HP/MP Mapper")
print(f"=" * 60)
for i, (p, d) in enumerate(zip(paths, datas)):
    print(f"  Save {i}: {p} ({len(d):,} bytes)")
print()

# Find battle overlay markers (0021) in each save
print("=== Battle overlay markers (0021) ===")
all_markers = []
for i, (label, data) in enumerate(zip(['before', 'damaged', 'mp_used'][:len(datas)], datas)):
    markers = find_markers(data, marker_id=b'\x00\x21')
    print(f"\n  {label}: {len(markers)} overlay markers")
    for m in markers:
        print(f"    0x{m['offset']:06x}: marker={m['marker_id'].hex()} tail={m['tail']} name='{m['name']}'")
        print(f"      stats[0:10]: {m['stats'][:10]}")
        # Show non-zero fields
        nonzero = [(j, v) for j, v in enumerate(m['stats']) if v != 0]
        print(f"      non-zero fields: {nonzero}")
    all_markers.append(markers)

# Diff markers between saves
if len(datas) >= 2:
    print(f"\n\n=== Diff: before vs damaged ===")
    before_markers = all_markers[0]
    after_markers = all_markers[1]
    
    for i, (bm, am) in enumerate(zip(before_markers, after_markers)):
        print(f"\n  Marker pair {i}:")
        print(f"    Before: 0x{bm['offset']:06x} name='{bm['name']}'")
        print(f"    After:  0x{am['offset']:06x} name='{am['name']}'")
        
        diffs = []
        for j in range(min(len(bm['stats']), len(am['stats']))):
            if bm['stats'][j] != am['stats'][j]:
                diffs.append((j, bm['stats'][j], am['stats'][j]))
        
        if diffs:
            print(f"    Changed fields:")
            for field_idx, before_val, after_val in diffs:
                delta = after_val - before_val
                print(f"      u16_{field_idx:02d}: {before_val} → {after_val} (Δ={delta})")
                # If this looks like HP damage (negative delta, reasonable magnitude)
                if delta < 0 and abs(delta) < 500:
                    print(f"        *** LIKELY CURRENT HP (took {abs(delta)} damage) ***")
                # If this looks like MP usage (negative delta, small magnitude)
                if delta < 0 and abs(delta) < 100:
                    print(f"        *** LIKELY CURRENT MP (used {abs(delta)} MP) ***")
        else:
            print(f"    (no stat changes)")

# Also check base markers (0011) for comparison
print(f"\n\n=== Base markers (0011) for comparison ===")
for i, (label, data) in enumerate(zip(['before', 'damaged', 'mp_used'][:len(datas)], datas)):
    markers = find_markers(data, marker_id=b'\x00\x11')
    print(f"\n  {label}: {len(markers)} base markers")
    for m in markers[:5]:  # Limit to first 5
        print(f"    0x{m['offset']:06x}: name='{m['name']}' stats[0:5]={m['stats'][:5]}")
