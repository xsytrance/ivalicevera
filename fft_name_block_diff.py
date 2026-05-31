#!/usr/bin/env python3
"""
FFT Local Name-Block Diff
Compares bytes near a specific character name across job-change saves.
Usage: python fft_name_block_diff.py <name> <save1.bin> <save2.bin> [save3.bin ...]
"""
import struct
import sys
from pathlib import Path

def find_name_blocks(data, name, region_start=0x31000, region_end=0x45000):
    """Find all offsets where 'name\\x00' appears in the data."""
    search = name.encode('ascii') + b'\x00'
    positions = []
    pos = region_start
    while pos < region_end:
        idx = data.find(search, pos, region_end)
        if idx == -1:
            break
        positions.append(idx)
        pos = idx + 1
    return positions

def analyze_block(data, name_off, window_before=256, window_after=512, region_start=0x31000, region_end=0x45000):
    """Extract the extended record block around a character name."""
    s = max(region_start, name_off - window_before)
    e = min(region_end, name_off + window_after)
    
    # Pre-name stat block (last 80 bytes before name = 40 u16)
    pre_start = name_off - 80
    if pre_start < 0:
        pre_start = 0
    pre_u16 = [struct.unpack_from('<H', data, pre_start + i*2)[0] for i in range((name_off - pre_start) // 2)]
    
    # Name and post-name
    name_start = name_off
    # Find end of name (null terminator)
    name_end = name_off
    while name_end < len(data) and data[name_end] != 0:
        name_end += 1
    name_end += 1  # include null
    
    # Check for extra string after name
    extra_str = b""
    if name_end < len(data) and data[name_end] != 0:
        extra_end = data.find(b'\x00', name_end, min(name_end + 20, len(data)))
        if extra_end > name_end:
            extra_str = data[name_end:extra_end + 1]
            name_end = extra_end + 1
    
    # Skip zeros to first non-zero metadata
    meta_start = name_end
    while meta_start < len(data) and data[meta_start] == 0:
        meta_start += 1
    
    meta_bytes = data[meta_start:min(meta_start + 32, len(data))]
    
    return {
        'pre_u16': pre_u16,
        'name_start': name_start,
        'name_end': name_start + len(data[name_start:name_end]),
        'extra_str': extra_str,
        'name_full': data[name_start:name_end],
        'meta_start': meta_start,
        'meta_bytes': meta_bytes,
        'meta_u8': list(meta_bytes),
        'meta_u16': [struct.unpack_from('<H', meta_bytes, i*2)[0] for i in range(len(meta_bytes)//2)],
        'raw_block': data[s:e],
    }

# Parse args
if len(sys.argv) < 4:
    print("Usage: python fft_name_block_diff.py <name> <save1.bin> <save2.bin> [save3.bin ...]")
    print("Example: python fft_name_block_diff.py OWL squire.bin archer.bin")
    sys.exit(1)

target_name = sys.argv[1]
save_paths = [Path(p) for p in sys.argv[2:]]
labels = [p.stem if p.stem else f'save{i}' for i, p in enumerate(save_paths)]

datas = []
for p in save_paths:
    if not p.exists():
        print(f"ERROR: {p} not found")
        sys.exit(1)
    datas.append(p.read_bytes())

print(f"Name-Block Diff: {target_name}")
print(f"Saves: {', '.join(f'{l} ({len(d):,}B)' for l, d in zip(labels, datas))}")
print()

# Find name in each save
all_blocks = []
for label, data in zip(labels, datas):
    positions = find_name_blocks(data, target_name)
    if not positions:
        print(f"WARNING: '{target_name}' not found in {label}")
        # Try all regions
        positions = find_name_blocks(data, target_name, 0, len(data))
        if positions:
            print(f"  Found at 0x{positions[0]:x} (outside extended region)")
    
    blocks = [analyze_block(data, pos) for pos in positions]
    all_blocks.append((label, blocks))

# Display each block
for label, blocks in all_blocks:
    for i, block in enumerate(blocks):
        print(f"\n{'='*60}")
        print(f"{label} block {i}:")
        print(f"  Full name: {block['name_full']!r}")
        print(f"  Pre-name u16[0:10]: {block['pre_u16'][:10]}")
        print(f"  Pre-name u16[10:20]: {block['pre_u16'][10:20]}")
        print(f"  Meta at 0x{block['meta_start']:x}: {block['meta_bytes'][:16].hex(' ')}")
        print(f"  Meta u8: {block['meta_u8'][:16]}")
        print(f"  Meta u16: {block['meta_u16'][:8]}")

# Diff blocks
if len(all_blocks) >= 2:
    print(f"\n\n{'='*60}")
    print("DIFF: Comparing first blocks")
    print(f"{'='*60}")
    
    ref_label, ref_blocks = all_blocks[0]
    ref_block = ref_blocks[0]
    
    for label, blocks in all_blocks[1:]:
        cmp_block = blocks[0]
        
        # Diff pre-name u16
        print(f"\n  {ref_label} vs {label} — pre-name u16:")
        max_len = max(len(ref_block['pre_u16']), len(cmp_block['pre_u16']))
        for i in range(max_len):
            rv = ref_block['pre_u16'][i] if i < len(ref_block['pre_u16']) else None
            cv = cmp_block['pre_u16'][i] if i < len(cmp_block['pre_u16']) else None
            if rv != cv:
                print(f"    [{i:2d}] {rv} → {cv} (Δ{cv-rv if rv and cv else '?'})")
        
        # Diff meta bytes
        print(f"\n  {ref_label} vs {label} — meta bytes:")
        if ref_block['meta_bytes'] != cmp_block['meta_bytes']:
            min_len = min(len(ref_block['meta_bytes']), len(cmp_block['meta_bytes']))
            for i in range(min_len):
                rv = ref_block['meta_bytes'][i]
                cv = cmp_block['meta_bytes'][i]
                if rv != cv:
                    # Calculate offset from name
                    name_off = ref_block['name_start']
                    meta_off = ref_block['meta_start'] + i
                    rel = meta_off - name_off
                    print(f"    meta[{i:2d}] (0x{meta_off:x}, rel_name={rel:+d}): {rv:02x} → {cv:02x}")
        else:
            print("    (identical)")
