#!/usr/bin/env python3
"""Find OWL marker-0011 and marker-0021 records in mid-battle autosave."""
import struct, pathlib

baseline = pathlib.Path('/home/xsyvps/fft-saves5/tactics/enhanced-1143/fftsave.bin').read_bytes()
mid = pathlib.Path('/home/xsyvps/fft-savesx/tactics/auto-x')

def find_marker(data, target_marker, target_tail):
    results = []
    for i in range(len(data) - 12):
        if data[i:i+2] != target_marker:
            continue
        if data[i+2:i+9] != b'\x11\x11\x11\x11\x11\x11\x11':
            continue
        tail = data[i+9:i+12]
        if tail != target_tail:
            continue
        for bl in range(70, 120):
            no = i + 12 + bl
            if no >= len(data):
                break
            if 0x20 <= data[no] < 0x7f:
                end = no
                while end < len(data) and 0x20 <= data[end] < 0x7f:
                    end += 1
                if 3 <= end - no <= 24 and end < len(data) and data[end] == 0:
                    name = data[no:end].decode('ascii')
                    stats = list(struct.unpack_from(f'<{bl//2}H', data, i+12))
                    results.append((name, i, bl, stats, tail))
                    break
    return results

# Baseline OWL stats (unshifted)
base_owl_off = 0x28bcb
base_owl = list(struct.unpack_from('<46H', baseline, base_owl_off + 12))
base_owl_real = [v >> 8 for v in base_owl]

print("=== marker-0011 (NEW encoding) across all mid-battle files ===\n")
for f in sorted(mid.glob('*.sav')):
    data = f.read_bytes()
    recs = find_marker(data, b'\x00\x11', b'\x10\x11\x00')
    for name, offset, bl, stats, tail in recs:
        unshifted = [v >> 8 for v in stats]
        print(f"{f.name}: name='{name}' offset=0x{offset:x} block={bl}B")
        print(f"  Stats(unshift): {unshifted[:20]}")
        if name == 'OWL':
            diffs = [(j, base_owl_real[j], unshifted[j], unshifted[j]-base_owl_real[j])
                     for j in range(min(len(base_owl_real), len(unshifted)))
                     if base_owl_real[j] != unshifted[j]]
            if diffs:
                print(f"  vs baseline:")
                for idx, vb, vn, d in diffs:
                    print(f"    u16_{idx:02d}: {vb} → {vn} (delta {d})")
            else:
                print(f"  vs baseline: NO CHANGES")
        print()

print("\n=== marker-0021 (NEW encoding) across all mid-battle files ===\n")
for f in sorted(mid.glob('*.sav')):
    data = f.read_bytes()
    recs = find_marker(data, b'\x00\x21', b'\x10\x11\x00')
    for name, offset, bl, stats, tail in recs:
        unshifted = [v >> 8 for v in stats]
        nonzero = [(j, unshifted[j]) for j in range(len(unshifted)) if unshifted[j] != 0]
        print(f"{f.name}: name='{name}' offset=0x{offset:x} block={bl}B")
        print(f"  Stats(unshift): {unshifted[:20]}")
        print(f"  Non-zero: {nonzero[:10]}")
        print()
